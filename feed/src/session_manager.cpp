#include "session_manager.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <unistd.h>
#include <cstring>
#include <stdexcept>
#include <cstdio>

namespace b3 {

static constexpr size_t UDP_BUF_SIZE = 65536;

SessionManager::SessionManager(std::vector<ChannelConfig> channels,
                                OnQuote on_quote,
                                OnTrade on_trade,
                                OnHeartbeat on_hb)
    : parser_(std::move(on_quote), std::move(on_trade), std::move(on_hb))
{
    channels_.resize(channels.size());
    for (size_t i = 0; i < channels.size(); ++i)
        channels_[i].cfg = std::move(channels[i]);
}

SessionManager::~SessionManager() {
    stop();
}

void SessionManager::start() {
    running_.store(true);
    for (auto& ch : channels_) {
        if (!open_socket(ch)) {
            std::fprintf(stderr, "[session] failed to open socket for channel %s\n",
                         ch.cfg.channel_label.c_str());
            continue;
        }
        ch.recv_thread = std::thread(&SessionManager::recv_loop, this, std::ref(ch));
    }
}

void SessionManager::stop() {
    running_.store(false);
    for (auto& ch : channels_) {
        close_socket(ch);
        if (ch.recv_thread.joinable()) ch.recv_thread.join();
    }
}

bool SessionManager::open_socket(Channel& ch) {
    ch.sock_fd = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (ch.sock_fd < 0) return false;

    // Allow multiple sockets on same port (both A/B channels)
    int reuse = 1;
    ::setsockopt(ch.sock_fd, SOL_SOCKET, SO_REUSEPORT, &reuse, sizeof(reuse));
    ::setsockopt(ch.sock_fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    // Increase receive buffer to 8 MB
    int rcvbuf = 8 * 1024 * 1024;
    ::setsockopt(ch.sock_fd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));

    sockaddr_in addr{};
    addr.sin_family      = AF_INET;
    addr.sin_port        = htons(ch.cfg.port);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (::bind(ch.sock_fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
        ::close(ch.sock_fd); ch.sock_fd = -1; return false;
    }

    // Join multicast group on the specified source interface
    ip_mreq mreq{};
    if (::inet_pton(AF_INET, ch.cfg.multicast_group.c_str(), &mreq.imr_multiaddr) != 1) {
        ::close(ch.sock_fd); ch.sock_fd = -1; return false;
    }
    if (ch.cfg.source_ip.empty() || ch.cfg.source_ip == "0.0.0.0") {
        mreq.imr_interface.s_addr = INADDR_ANY;
    } else {
        ::inet_pton(AF_INET, ch.cfg.source_ip.c_str(), &mreq.imr_interface);
    }

    if (::setsockopt(ch.sock_fd, IPPROTO_IP, IP_ADD_MEMBERSHIP,
                     &mreq, sizeof(mreq)) != 0) {
        std::fprintf(stderr, "[session] IP_ADD_MEMBERSHIP failed for %s\n",
                     ch.cfg.multicast_group.c_str());
        // Don't abort — might work on loopback in dev
    }

    return true;
}

void SessionManager::close_socket(Channel& ch) {
    if (ch.sock_fd >= 0) {
        // Leave multicast group
        ip_mreq mreq{};
        ::inet_pton(AF_INET, ch.cfg.multicast_group.c_str(), &mreq.imr_multiaddr);
        mreq.imr_interface.s_addr = INADDR_ANY;
        ::setsockopt(ch.sock_fd, IPPROTO_IP, IP_DROP_MEMBERSHIP, &mreq, sizeof(mreq));

        ::shutdown(ch.sock_fd, SHUT_RD);
        ::close(ch.sock_fd);
        ch.sock_fd = -1;
    }
}

void SessionManager::recv_loop(Channel& ch) {
    uint8_t buf[UDP_BUF_SIZE];

    while (running_.load()) {
        ssize_t n = ::recv(ch.sock_fd, buf, sizeof(buf), 0);
        if (n <= 0) break;

        // parser_ is shared between A and B channels; it handles seq-num dedup internally
        parser_.parse(buf, static_cast<size_t>(n));
    }
}

} // namespace b3
