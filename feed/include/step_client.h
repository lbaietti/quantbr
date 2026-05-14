#pragma once
#include <string>
#include <cstdint>
#include <functional>
#include <atomic>
#include <thread>

// B3 STEP (Specialized Trade and Execution Protocol) — FIX-based order entry
// Wraps a TCP FIX session toward B3's entry gateway

namespace b3 {

enum class OrderSide  { BUY = '1', SELL = '2' };
enum class OrderType  { MARKET = '1', LIMIT = '2', STOP = '4' };
enum class TimeInForce { DAY = '0', IOC = '3', FOK = '4', GTD = '6' };

struct NewOrderRequest {
    std::string cl_ord_id;      // unique client order ID
    std::string symbol;
    uint32_t    security_id;
    OrderSide   side;
    OrderType   ord_type;
    TimeInForce tif;
    double      price;          // 0 for MARKET
    int64_t     qty;
    std::string account;
};

struct OrderAck {
    std::string cl_ord_id;
    std::string ord_id;         // exchange order ID
    char        status;         // '0'=New '1'=PartFill '2'=Fill '4'=Cancel '8'=Reject
    std::string text;
};

using OnOrderAck = std::function<void(const OrderAck&)>;

class StepClient {
public:
    StepClient(const std::string& host, uint16_t port,
               const std::string& sender_comp_id,
               const std::string& target_comp_id,
               const std::string& password,
               OnOrderAck on_ack);

    bool connect();
    void disconnect();
    bool is_connected() const { return connected_.load(); }

    bool send_new_order(const NewOrderRequest& req);
    bool send_cancel(const std::string& orig_cl_ord_id, const std::string& symbol, int64_t qty);
    bool send_cancel_replace(const std::string& orig_cl_ord_id, const NewOrderRequest& new_req);

private:
    void recv_loop();
    void send_heartbeat();
    std::string build_fix_header(const std::string& msg_type, int body_len);
    std::string compute_checksum(const std::string& msg);

    std::string host_;
    uint16_t    port_;
    std::string sender_comp_id_;
    std::string target_comp_id_;
    std::string password_;
    OnOrderAck  on_ack_;
    int         sock_fd_{-1};
    std::atomic<bool> connected_{false};
    std::thread recv_thread_;
    int         msg_seq_num_{1};
};

} // namespace b3
