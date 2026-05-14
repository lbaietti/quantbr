#pragma once
#include <string>
#include <memory>
#include "order_book.h"
#include "umdf_parser.h"

namespace b3 {

// Publishes BookSnapshot and TradeEvent over ZMQ PUB socket.
// Backend subscribes on tcp://localhost:<port> with topic "snapshot" or "trade".
class ZmqPublisher {
public:
    explicit ZmqPublisher(const std::string& endpoint);
    ~ZmqPublisher();

    // Non-copyable
    ZmqPublisher(const ZmqPublisher&)            = delete;
    ZmqPublisher& operator=(const ZmqPublisher&) = delete;

    void publish_snapshot(const BookSnapshot& snap);
    void publish_trade(const TradeEvent& trade);

private:
    void* ctx_{nullptr};
    void* sock_{nullptr};

    void send_frame(const std::string& topic, const std::string& payload);
};

} // namespace b3
