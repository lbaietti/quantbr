#include "step_client.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <ctime>
#include <sstream>
#include <iomanip>
#include <numeric>
#include <stdexcept>
#include <cstdio>

namespace b3 {

// ── Helpers ──────────────────────────────────────────────────────────────────

static std::string utc_timestamp() {
    timespec ts{};
    clock_gettime(CLOCK_REALTIME, &ts);
    std::tm tm{};
    gmtime_r(&ts.tv_sec, &tm);
    char buf[24];
    std::snprintf(buf, sizeof(buf), "%04d%02d%02d-%02d:%02d:%02d",
                  tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday,
                  tm.tm_hour, tm.tm_min, tm.tm_sec);
    return buf;
}

// FIX field: "tag=value\x01"
static std::string field(int tag, const std::string& val) {
    return std::to_string(tag) + '=' + val + '\x01';
}
static std::string field(int tag, int val) {
    return field(tag, std::to_string(val));
}
static std::string field(int tag, double val, int prec = 4) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(prec) << val;
    return field(tag, oss.str());
}

// ── StepClient ───────────────────────────────────────────────────────────────

StepClient::StepClient(const std::string& host, uint16_t port,
                       const std::string& sender_comp_id,
                       const std::string& target_comp_id,
                       const std::string& password,
                       OnOrderAck on_ack)
    : host_(host), port_(port)
    , sender_comp_id_(sender_comp_id)
    , target_comp_id_(target_comp_id)
    , password_(password)
    , on_ack_(std::move(on_ack))
{}

bool StepClient::connect() {
    sock_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
    if (sock_fd_ < 0) return false;

    // Disable Nagle for low-latency FIX
    int flag = 1;
    ::setsockopt(sock_fd_, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port   = htons(port_);
    if (::inet_pton(AF_INET, host_.c_str(), &addr.sin_addr) != 1) {
        ::close(sock_fd_); sock_fd_ = -1; return false;
    }

    if (::connect(sock_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        ::close(sock_fd_); sock_fd_ = -1; return false;
    }

    connected_.store(true);
    recv_thread_ = std::thread(&StepClient::recv_loop, this);

    // Send FIX Logon (35=A)
    std::string body;
    body += field(49, sender_comp_id_);   // SenderCompID
    body += field(56, target_comp_id_);   // TargetCompID
    body += field(34, msg_seq_num_++);    // MsgSeqNum
    body += field(52, utc_timestamp());   // SendingTime
    body += field(98, 0);                 // EncryptMethod = None
    body += field(108, 30);               // HeartBtInt = 30s
    body += field(554, password_);        // Password

    std::string msg = build_fix_header("A", static_cast<int>(body.size())) + body;
    msg += field(10, compute_checksum(msg)); // CheckSum

    ::send(sock_fd_, msg.data(), msg.size(), 0);
    return true;
}

void StepClient::disconnect() {
    connected_.store(false);
    if (sock_fd_ >= 0) {
        ::shutdown(sock_fd_, SHUT_RDWR);
        ::close(sock_fd_);
        sock_fd_ = -1;
    }
    if (recv_thread_.joinable()) recv_thread_.join();
}

bool StepClient::send_new_order(const NewOrderRequest& req) {
    if (!connected_.load()) return false;

    std::string body;
    body += field(49, sender_comp_id_);
    body += field(56, target_comp_id_);
    body += field(34, msg_seq_num_++);
    body += field(52, utc_timestamp());
    body += field(11, req.cl_ord_id);                                          // ClOrdID
    body += field(55, req.symbol);                                             // Symbol
    body += field(48, std::to_string(req.security_id));                        // SecurityID
    body += field(22, 8);                                                      // SecurityIDSource = Exchange
    body += field(54, std::string(1, static_cast<char>(req.side)));            // Side
    body += field(40, std::string(1, static_cast<char>(req.ord_type)));        // OrdType
    body += field(59, std::string(1, static_cast<char>(req.tif)));             // TimeInForce
    if (req.ord_type != OrderType::MARKET)
        body += field(44, req.price);                                          // Price
    body += field(38, static_cast<int>(req.qty));                              // OrderQty
    body += field(1, req.account);                                             // Account

    std::string msg = build_fix_header("D", static_cast<int>(body.size())) + body;
    msg += field(10, compute_checksum(msg));

    return ::send(sock_fd_, msg.data(), msg.size(), 0) > 0;
}

bool StepClient::send_cancel(const std::string& orig_cl_ord_id,
                              const std::string& symbol, int64_t qty) {
    if (!connected_.load()) return false;

    std::string body;
    body += field(49, sender_comp_id_);
    body += field(56, target_comp_id_);
    body += field(34, msg_seq_num_++);
    body += field(52, utc_timestamp());
    body += field(41, orig_cl_ord_id);          // OrigClOrdID
    body += field(11, orig_cl_ord_id + "_C");   // ClOrdID
    body += field(55, symbol);
    body += field(38, static_cast<int>(qty));

    std::string msg = build_fix_header("F", static_cast<int>(body.size())) + body;
    msg += field(10, compute_checksum(msg));

    return ::send(sock_fd_, msg.data(), msg.size(), 0) > 0;
}

bool StepClient::send_cancel_replace(const std::string& orig_cl_ord_id,
                                      const NewOrderRequest& new_req) {
    if (!connected_.load()) return false;

    std::string body;
    body += field(49, sender_comp_id_);
    body += field(56, target_comp_id_);
    body += field(34, msg_seq_num_++);
    body += field(52, utc_timestamp());
    body += field(41, orig_cl_ord_id);
    body += field(11, new_req.cl_ord_id);
    body += field(55, new_req.symbol);
    body += field(48, std::to_string(new_req.security_id));
    body += field(22, 8);
    body += field(54, std::string(1, static_cast<char>(new_req.side)));
    body += field(40, std::string(1, static_cast<char>(new_req.ord_type)));
    body += field(59, std::string(1, static_cast<char>(new_req.tif)));
    if (new_req.ord_type != OrderType::MARKET)
        body += field(44, new_req.price);
    body += field(38, static_cast<int>(new_req.qty));

    std::string msg = build_fix_header("G", static_cast<int>(body.size())) + body;
    msg += field(10, compute_checksum(msg));

    return ::send(sock_fd_, msg.data(), msg.size(), 0) > 0;
}

// ── Private ──────────────────────────────────────────────────────────────────

void StepClient::recv_loop() {
    char buf[4096];
    std::string acc; // accumulate partial FIX messages

    while (connected_.load()) {
        ssize_t n = ::recv(sock_fd_, buf, sizeof(buf), 0);
        if (n <= 0) break;

        acc.append(buf, static_cast<size_t>(n));

        // FIX messages end with "10=NNN\x01"; split on that
        size_t pos;
        while ((pos = acc.find("10=")) != std::string::npos) {
            size_t end = acc.find('\x01', pos);
            if (end == std::string::npos) break;
            std::string msg = acc.substr(0, end + 1);
            acc.erase(0, end + 1);

            // Parse exec report (35=8)
            auto extract = [&](const std::string& tag) -> std::string {
                std::string needle = '\x01' + tag + '=';
                size_t p = msg.find(needle);
                if (p == std::string::npos) {
                    // try start of message
                    if (msg.substr(0, tag.size() + 1) == tag + '=')
                        p = std::string::npos; // not found at start
                    return "";
                }
                p += needle.size();
                size_t e = msg.find('\x01', p);
                return msg.substr(p, e - p);
            };

            std::string msg_type = extract("35");
            if (msg_type == "8" && on_ack_) { // ExecutionReport
                OrderAck ack;
                ack.cl_ord_id = extract("11");
                ack.ord_id    = extract("37");
                std::string status = extract("39");
                ack.status    = status.empty() ? '8' : status[0];
                ack.text      = extract("58");
                on_ack_(ack);
            }
            // 35=0 = Heartbeat, 35=1 = TestRequest — ignore for now
        }
    }

    connected_.store(false);
}

std::string StepClient::build_fix_header(const std::string& msg_type, int body_len) {
    std::string hdr;
    hdr += field(8, "FIX.4.4");          // BeginString
    // BodyLength (tag 9) = everything after tag 9 up to but not incl. checksum
    // We set it after assembling body; for now placeholder, recomputed externally
    hdr += field(9, body_len);
    hdr += field(35, msg_type);
    return hdr;
}

std::string StepClient::compute_checksum(const std::string& msg) {
    unsigned int sum = 0;
    for (unsigned char c : msg) sum += c;
    char buf[4];
    std::snprintf(buf, sizeof(buf), "%03u", sum % 256);
    return buf;
}

} // namespace b3
