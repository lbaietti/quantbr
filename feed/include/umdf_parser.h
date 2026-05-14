#pragma once
#include <cstdint>
#include <cstring>
#include <string>
#include <functional>
#include <arpa/inet.h>

// B3 UMDF (Unified Market Data Feed) — binary UDP multicast protocol
// Reference: B3 MarketData/UMDF Technical Specification v2.x

namespace b3 {

// ----- Wire types (big-endian on the wire) -----
using Price4  = int64_t;   // price * 10000
using Price8  = int64_t;   // price * 100000000
using Qty     = int64_t;
using SeqNum  = uint32_t;
using MsgType = char[2];

#pragma pack(push, 1)

struct PacketHeader {
    uint32_t seq_num;
    uint64_t send_time;   // nanoseconds since epoch
    uint8_t  msg_count;
};

struct MessageHeader {
    uint16_t msg_size;
    char     msg_type[2];
};

// MsgType "W" — Market Data Snapshot Full Refresh
struct MDSnapshotFullRefresh {
    uint32_t trade_date;
    uint64_t trad_ses_open_time;
    uint64_t transact_time;
    int32_t  md_update_action;     // 0=New 1=Change 2=Delete
    int32_t  md_entry_type;        // 0=Bid 1=Offer 2=Trade 4=Open 5=Close
    Price8   md_entry_px;
    Qty      md_entry_size;
    int32_t  rpt_seq;
    char     symbol[12];
    char     security_id[8];       // B3 numeric security ID (ASCII)
};

// MsgType "X" — Market Data Incremental Refresh
struct MDIncrementalRefresh {
    uint64_t transact_time;
    uint8_t  match_event_indicator;
};

struct MDEntry {
    int32_t  md_update_action;
    int32_t  md_entry_type;
    Price8   md_entry_px;
    Qty      md_entry_size;
    uint32_t security_id;
    int32_t  rpt_seq;
    uint8_t  number_of_orders;
    int32_t  md_price_level;
    uint64_t transact_time;
};

// MsgType "d" — Security Definition
struct SecurityDefinition {
    char     symbol[12];
    char     security_id[8];
    char     security_type[6];      // "OPT", "FUT", "CS" (cash stock)
    char     mat_date[9];
    Price8   strike_price;
    char     put_or_call[2];        // "P" or "C"
    char     currency[4];
    int32_t  min_trade_vol;
    int32_t  lot_size;
};

#pragma pack(pop)

// ---- Parsed event structs (host byte order) ----

struct QuoteEvent {
    uint64_t timestamp_ns;
    uint32_t security_id;
    char     symbol[12];
    double   bid;
    double   ask;
    int64_t  bid_qty;
    int64_t  ask_qty;
};

struct TradeEvent {
    uint64_t timestamp_ns;
    uint32_t security_id;
    char     symbol[12];
    double   price;
    int64_t  qty;
    char     aggressor_side;   // 'B' buy, 'S' sell
};

struct BookLevel {
    double  price;
    int64_t qty;
    int32_t order_count;
};

// Callbacks
using OnQuote   = std::function<void(const QuoteEvent&)>;
using OnTrade   = std::function<void(const TradeEvent&)>;
using OnHeartbeat = std::function<void(uint64_t timestamp_ns)>;

class UMDFParser {
public:
    explicit UMDFParser(OnQuote on_quote, OnTrade on_trade, OnHeartbeat on_hb = nullptr);

    // Feed raw UDP payload; returns number of messages parsed
    int parse(const uint8_t* buf, size_t len);

    void set_seq_gap_callback(std::function<void(SeqNum expected, SeqNum got)> cb);

private:
    void handle_snapshot(const uint8_t* body, uint16_t size);
    void handle_incremental(const uint8_t* body, uint16_t size);

    OnQuote     on_quote_;
    OnTrade     on_trade_;
    OnHeartbeat on_heartbeat_;
    std::function<void(SeqNum, SeqNum)> on_gap_;
    SeqNum last_seq_{0};
};

} // namespace b3
