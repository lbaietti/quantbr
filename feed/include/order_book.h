#pragma once
#include <map>
#include <unordered_map>
#include <string>
#include <cstdint>
#include <optional>
#include "umdf_parser.h"

namespace b3 {

struct L2Level {
    double  price;
    int64_t qty;
    int32_t order_count;
};

struct BookSnapshot {
    uint32_t security_id;
    char     symbol[12];
    uint64_t last_update_ns;
    double   last_trade_price;
    int64_t  last_trade_qty;
    double   vwap;
    int64_t  total_traded_qty;
    double   total_traded_value;
    // Top 5 levels
    L2Level bids[5];
    L2Level asks[5];
    int     bid_depth;
    int     ask_depth;
};

class OrderBook {
public:
    explicit OrderBook(uint32_t security_id, const char* symbol);

    void apply_bid(double price, int64_t qty, int action);
    void apply_ask(double price, int64_t qty, int action);
    void apply_trade(double price, int64_t qty, char aggressor);

    double best_bid() const;
    double best_ask() const;
    double mid() const;
    double spread() const;
    double vwap() const;

    BookSnapshot snapshot() const;

private:
    // price → qty (bids descending, asks ascending)
    std::map<double, int64_t, std::greater<double>> bids_;
    std::map<double, int64_t>                        asks_;

    uint32_t security_id_;
    char     symbol_[12];
    uint64_t last_update_ns_{0};
    double   last_trade_price_{0};
    int64_t  last_trade_qty_{0};
    double   sum_price_qty_{0};
    int64_t  total_traded_qty_{0};
};

// Manages all instruments' order books
class BookManager {
public:
    OrderBook& get_or_create(uint32_t security_id, const char* symbol);
    OrderBook* find(uint32_t security_id);
    std::optional<BookSnapshot> snapshot(uint32_t security_id);

private:
    std::unordered_map<uint32_t, OrderBook> books_;
};

} // namespace b3
