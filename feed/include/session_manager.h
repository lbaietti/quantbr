#pragma once
#include <string>
#include <vector>
#include <functional>
#include <thread>
#include <atomic>
#include "umdf_parser.h"

namespace b3 {

// Configuration for one UMDF multicast channel (A or B).
struct ChannelConfig {
    std::string multicast_group;
    std::string source_ip;     // interface IP for multicast join
    uint16_t    port;
    std::string channel_label; // "A" or "B"
};

// Manages one or more UDP multicast receive loops, feeds raw packets into UMDFParser.
// B3 provides channel A and B for redundancy; we listen to both and de-duplicate by seq_num.
class SessionManager {
public:
    SessionManager(std::vector<ChannelConfig> channels,
                   OnQuote on_quote,
                   OnTrade on_trade,
                   OnHeartbeat on_hb = nullptr);
    ~SessionManager();

    SessionManager(const SessionManager&)            = delete;
    SessionManager& operator=(const SessionManager&) = delete;

    void start();
    void stop();
    bool is_running() const { return running_.load(); }

    void set_gap_callback(std::function<void(SeqNum, SeqNum)> cb) {
        parser_.set_seq_gap_callback(std::move(cb));
    }

private:
    struct Channel {
        ChannelConfig cfg;
        int           sock_fd{-1};
        std::thread   recv_thread;
    };

    void recv_loop(Channel& ch);
    bool open_socket(Channel& ch);
    void close_socket(Channel& ch);

    std::vector<Channel> channels_;
    UMDFParser           parser_;
    std::atomic<bool>    running_{false};
};

} // namespace b3
