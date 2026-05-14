#include "order_book.h"
#include <cstring>
#include <algorithm>

namespace b3 {

// ── OrderBook ────────────────────────────────────────────────────────────────

OrderBook::OrderBook(uint32_t security_id, const char* symbol)
    : security_id_(security_id)
{
    std::strncpy(symbol_, symbol, sizeof(symbol_) - 1);
    symbol_[sizeof(symbol_) - 1] = '\0';
}

void OrderBook::apply_bid(double price, int64_t qty, int action) {
    // action: 0=New, 1=Change, 2=Delete
    if (action == 2 || qty == 0) {
        bids_.erase(price);
    } else {
        bids_[price] = qty;
    }
}

void OrderBook::apply_ask(double price, int64_t qty, int action) {
    if (action == 2 || qty == 0) {
        asks_.erase(price);
    } else {
        asks_[price] = qty;
    }
}

void OrderBook::apply_trade(double price, int64_t qty, char aggressor) {
    (void)aggressor;
    last_trade_price_ = price;
    last_trade_qty_   = qty;
    sum_price_qty_   += price * static_cast<double>(qty);
    total_traded_qty_ += qty;
}

double OrderBook::best_bid() const {
    return bids_.empty() ? 0.0 : bids_.begin()->first;
}

double OrderBook::best_ask() const {
    return asks_.empty() ? 0.0 : asks_.begin()->first;
}

double OrderBook::mid() const {
    double bb = best_bid();
    double ba = best_ask();
    if (bb == 0.0 || ba == 0.0) return 0.0;
    return (bb + ba) / 2.0;
}

double OrderBook::spread() const {
    double bb = best_bid();
    double ba = best_ask();
    if (bb == 0.0 || ba == 0.0) return 0.0;
    return ba - bb;
}

double OrderBook::vwap() const {
    if (total_traded_qty_ == 0) return 0.0;
    return sum_price_qty_ / static_cast<double>(total_traded_qty_);
}

BookSnapshot OrderBook::snapshot() const {
    BookSnapshot snap{};
    snap.security_id       = security_id_;
    snap.last_update_ns    = last_update_ns_;
    snap.last_trade_price  = last_trade_price_;
    snap.last_trade_qty    = last_trade_qty_;
    snap.vwap              = vwap();
    snap.total_traded_qty  = total_traded_qty_;
    snap.total_traded_value = sum_price_qty_;

    std::strncpy(snap.symbol, symbol_, sizeof(snap.symbol) - 1);

    int bi = 0;
    for (const auto& [price, qty] : bids_) {
        if (bi >= 5) break;
        snap.bids[bi++] = {price, qty, 0};
    }
    snap.bid_depth = bi;

    int ai = 0;
    for (const auto& [price, qty] : asks_) {
        if (ai >= 5) break;
        snap.asks[ai++] = {price, qty, 0};
    }
    snap.ask_depth = ai;

    return snap;
}

// ── BookManager ──────────────────────────────────────────────────────────────

OrderBook& BookManager::get_or_create(uint32_t security_id, const char* symbol) {
    auto it = books_.find(security_id);
    if (it == books_.end()) {
        it = books_.emplace(
            std::piecewise_construct,
            std::forward_as_tuple(security_id),
            std::forward_as_tuple(security_id, symbol)
        ).first;
    }
    return it->second;
}

OrderBook* BookManager::find(uint32_t security_id) {
    auto it = books_.find(security_id);
    return (it == books_.end()) ? nullptr : &it->second;
}

std::optional<BookSnapshot> BookManager::snapshot(uint32_t security_id) {
    auto* book = find(security_id);
    if (!book) return std::nullopt;
    return book->snapshot();
}

} // namespace b3
