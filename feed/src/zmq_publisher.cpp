#include "zmq_publisher.h"
#include <zmq.h>
#include <stdexcept>
#include <cstring>
#include <sstream>
#include <iomanip>
#include <cstdio>

namespace b3 {

ZmqPublisher::ZmqPublisher(const std::string& endpoint) {
    ctx_  = zmq_ctx_new();
    sock_ = zmq_socket(ctx_, ZMQ_PUB);

    int linger = 0;
    zmq_setsockopt(sock_, ZMQ_LINGER, &linger, sizeof(linger));

    if (zmq_bind(sock_, endpoint.c_str()) != 0) {
        zmq_close(sock_);
        zmq_ctx_destroy(ctx_);
        throw std::runtime_error(std::string("zmq_bind failed: ") + zmq_strerror(zmq_errno()));
    }
}

ZmqPublisher::~ZmqPublisher() {
    if (sock_) zmq_close(sock_);
    if (ctx_)  zmq_ctx_destroy(ctx_);
}

// ── Serialization helpers ─────────────────────────────────────────────────────

static std::string level_json(const L2Level& l) {
    char buf[64];
    std::snprintf(buf, sizeof(buf), R"({"price":%.4f,"qty":%lld,"orders":%d})",
                  l.price,
                  static_cast<long long>(l.qty),
                  l.order_count);
    return buf;
}

static std::string levels_array(const L2Level* levels, int depth) {
    std::string out = "[";
    for (int i = 0; i < depth; ++i) {
        if (i) out += ',';
        out += level_json(levels[i]);
    }
    out += ']';
    return out;
}

void ZmqPublisher::publish_snapshot(const BookSnapshot& snap) {
    // Symbol is a fixed-length char array; ensure null termination
    char sym[13]{};
    std::strncpy(sym, snap.symbol, 12);

    char buf[1024];
    std::snprintf(buf, sizeof(buf),
        R"({"type":"snapshot","security_id":%u,"symbol":"%s","ts":%llu,)"
        R"("last_px":%.4f,"last_qty":%lld,"vwap":%.4f,)"
        R"("total_qty":%lld,"total_val":%.4f,)"
        R"("bids":%s,"asks":%s})",
        snap.security_id,
        sym,
        static_cast<unsigned long long>(snap.last_update_ns),
        snap.last_trade_price,
        static_cast<long long>(snap.last_trade_qty),
        snap.vwap,
        static_cast<long long>(snap.total_traded_qty),
        snap.total_traded_value,
        levels_array(snap.bids, snap.bid_depth).c_str(),
        levels_array(snap.asks, snap.ask_depth).c_str()
    );

    send_frame("snapshot", buf);
}

void ZmqPublisher::publish_trade(const TradeEvent& trade) {
    char sym[13]{};
    std::strncpy(sym, trade.symbol, 12);

    char buf[256];
    std::snprintf(buf, sizeof(buf),
        R"({"type":"trade","security_id":%u,"symbol":"%s","ts":%llu,)"
        R"("price":%.4f,"qty":%lld,"aggressor":"%c"})",
        trade.security_id,
        sym,
        static_cast<unsigned long long>(trade.timestamp_ns),
        trade.price,
        static_cast<long long>(trade.qty),
        trade.aggressor_side
    );

    send_frame("trade", buf);
}

void ZmqPublisher::send_frame(const std::string& topic, const std::string& payload) {
    // ZMQ multipart: [topic][payload]
    zmq_send(sock_, topic.data(), topic.size(), ZMQ_SNDMORE);
    zmq_send(sock_, payload.data(), payload.size(), 0);
}

} // namespace b3
