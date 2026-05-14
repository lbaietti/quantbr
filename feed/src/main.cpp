#include "session_manager.h"
#include "order_book.h"
#include "zmq_publisher.h"
#include "step_client.h"
#include <cstdlib>
#include <cstdio>
#include <csignal>
#include <atomic>
#include <string>
#include <memory>

// ── Config from environment ───────────────────────────────────────────────────
// Required:
//   B3_MCAST_GROUP_A   e.g. "233.200.79.1"
//   B3_MCAST_GROUP_B   e.g. "233.200.79.2"
//   B3_MCAST_PORT      e.g. "20000"
//   B3_SOURCE_IP       local interface IP, e.g. "192.168.1.10"
//   B3_ZMQ_ENDPOINT    e.g. "tcp://0.0.0.0:5555"
//
// Optional (order entry):
//   B3_STEP_HOST       B3 gateway IP
//   B3_STEP_PORT       default 21000
//   B3_SENDER_COMP_ID
//   B3_TARGET_COMP_ID
//   B3_PASSWORD

static std::string env(const char* key, const char* dflt = "") {
    const char* v = std::getenv(key);
    return v ? v : dflt;
}

static std::atomic<bool> g_shutdown{false};

static void on_signal(int) { g_shutdown.store(true); }

int main() {
    std::signal(SIGINT,  on_signal);
    std::signal(SIGTERM, on_signal);

    // ── ZMQ publisher ─────────────────────────────────────────────────────────
    std::string zmq_endpoint = env("B3_ZMQ_ENDPOINT", "tcp://0.0.0.0:5555");
    std::unique_ptr<b3::ZmqPublisher> pub;
    try {
        pub = std::make_unique<b3::ZmqPublisher>(zmq_endpoint);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "[main] ZMQ init failed: %s\n", e.what());
        return 1;
    }
    std::printf("[main] ZMQ publisher bound to %s\n", zmq_endpoint.c_str());

    // ── Order books ───────────────────────────────────────────────────────────
    b3::BookManager books;

    // ── Market data callbacks ─────────────────────────────────────────────────
    auto on_quote = [&](const b3::QuoteEvent& q) {
        auto& book = books.get_or_create(q.security_id, q.symbol);
        if (q.bid > 0) book.apply_bid(q.bid, q.bid_qty, 0);
        if (q.ask > 0) book.apply_ask(q.ask, q.ask_qty, 0);

        pub->publish_snapshot(book.snapshot());
    };

    auto on_trade = [&](const b3::TradeEvent& t) {
        auto* book = books.find(t.security_id);
        if (book) {
            book->apply_trade(t.price, t.qty, t.aggressor_side);
            pub->publish_snapshot(book->snapshot());
        }
        pub->publish_trade(t);
    };

    auto on_hb = [](uint64_t ts) {
        (void)ts; // heartbeat — can log or monitor latency here
    };

    auto on_gap = [](b3::SeqNum expected, b3::SeqNum got) {
        std::fprintf(stderr, "[feed] seq gap: expected %u got %u (missed %u pkts)\n",
                     expected, got, got - expected);
    };

    // ── Multicast session ─────────────────────────────────────────────────────
    std::string mcast_a   = env("B3_MCAST_GROUP_A", "233.200.79.1");
    std::string mcast_b   = env("B3_MCAST_GROUP_B", "233.200.79.2");
    uint16_t    mcast_port = static_cast<uint16_t>(std::stoi(env("B3_MCAST_PORT", "20000")));
    std::string source_ip  = env("B3_SOURCE_IP", "0.0.0.0");

    std::vector<b3::ChannelConfig> channels = {
        {mcast_a, source_ip, mcast_port, "A"},
        {mcast_b, source_ip, mcast_port, "B"},
    };

    b3::SessionManager session(std::move(channels), on_quote, on_trade, on_hb);
    session.set_gap_callback(on_gap);

    std::printf("[main] joining multicast %s and %s port %u\n",
                mcast_a.c_str(), mcast_b.c_str(), mcast_port);
    session.start();

    // ── Optional STEP order-entry client ──────────────────────────────────────
    std::unique_ptr<b3::StepClient> step;
    std::string step_host = env("B3_STEP_HOST");
    if (!step_host.empty()) {
        uint16_t step_port = static_cast<uint16_t>(
            std::stoi(env("B3_STEP_PORT", "21000")));

        auto on_ack = [](const b3::OrderAck& ack) {
            std::printf("[step] ack cl_ord_id=%s ord_id=%s status=%c text=%s\n",
                        ack.cl_ord_id.c_str(), ack.ord_id.c_str(),
                        ack.status, ack.text.c_str());
        };

        step = std::make_unique<b3::StepClient>(
            step_host, step_port,
            env("B3_SENDER_COMP_ID", "QUANTBR"),
            env("B3_TARGET_COMP_ID", "B3"),
            env("B3_PASSWORD"),
            on_ack
        );

        if (!step->connect()) {
            std::fprintf(stderr, "[main] STEP connect failed — running market-data only\n");
            step.reset();
        } else {
            std::printf("[main] STEP connected to %s:%u\n", step_host.c_str(), step_port);
        }
    }

    // ── Run until signal ──────────────────────────────────────────────────────
    std::printf("[main] running — press Ctrl+C to stop\n");
    while (!g_shutdown.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    std::printf("\n[main] shutting down…\n");
    session.stop();
    if (step) step->disconnect();

    return 0;
}
