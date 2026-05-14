#include "umdf_parser.h"
#include <cstring>
#include <cstdio>

namespace b3 {

UMDFParser::UMDFParser(OnQuote on_quote, OnTrade on_trade, OnHeartbeat on_hb)
    : on_quote_(std::move(on_quote))
    , on_trade_(std::move(on_trade))
    , on_heartbeat_(std::move(on_hb))
{}

void UMDFParser::set_seq_gap_callback(std::function<void(SeqNum, SeqNum)> cb) {
    on_gap_ = std::move(cb);
}

int UMDFParser::parse(const uint8_t* buf, size_t len) {
    if (len < sizeof(PacketHeader)) return 0;

    const auto* pkt = reinterpret_cast<const PacketHeader*>(buf);
    SeqNum seq = ntohl(pkt->seq_num);

    if (last_seq_ != 0 && seq != last_seq_ + 1) {
        if (on_gap_) on_gap_(last_seq_ + 1, seq);
    }
    last_seq_ = seq;

    uint64_t send_time;
    std::memcpy(&send_time, &pkt->send_time, sizeof(send_time));
    // send_time is big-endian 64-bit
    send_time = be64toh(send_time);

    if (on_heartbeat_ && pkt->msg_count == 0) {
        on_heartbeat_(send_time);
        return 0;
    }

    const uint8_t* cursor = buf + sizeof(PacketHeader);
    const uint8_t* end    = buf + len;
    int parsed = 0;

    for (uint8_t i = 0; i < pkt->msg_count && cursor < end; ++i) {
        if (cursor + sizeof(MessageHeader) > end) break;

        const auto* mh = reinterpret_cast<const MessageHeader*>(cursor);
        uint16_t msg_size;
        std::memcpy(&msg_size, &mh->msg_size, sizeof(msg_size));
        msg_size = ntohs(msg_size);

        if (cursor + msg_size > end) break;

        const uint8_t* body      = cursor + sizeof(MessageHeader);
        uint16_t       body_size = msg_size - static_cast<uint16_t>(sizeof(MessageHeader));

        if (mh->msg_type[0] == 'X') {
            handle_incremental(body, body_size);
        } else if (mh->msg_type[0] == 'W') {
            handle_snapshot(body, body_size);
        }
        // 'd' (SecurityDefinition) handled elsewhere if needed

        cursor += msg_size;
        ++parsed;
    }

    return parsed;
}

static double price8_to_double(int64_t p) {
    return static_cast<double>(p) / 1e8;
}

void UMDFParser::handle_snapshot(const uint8_t* body, uint16_t size) {
    if (size < sizeof(MDSnapshotFullRefresh)) return;

    MDSnapshotFullRefresh snap{};
    std::memcpy(&snap, body, sizeof(snap));

    // Convert to host byte order
    snap.transact_time  = be64toh(snap.transact_time);
    snap.md_update_action = static_cast<int32_t>(ntohl(static_cast<uint32_t>(snap.md_update_action)));
    snap.md_entry_type    = static_cast<int32_t>(ntohl(static_cast<uint32_t>(snap.md_entry_type)));

    int64_t raw_px;
    std::memcpy(&raw_px, &snap.md_entry_px, sizeof(raw_px));
    raw_px = static_cast<int64_t>(be64toh(static_cast<uint64_t>(raw_px)));

    int64_t raw_qty;
    std::memcpy(&raw_qty, &snap.md_entry_size, sizeof(raw_qty));
    raw_qty = static_cast<int64_t>(be64toh(static_cast<uint64_t>(raw_qty)));

    double  price = price8_to_double(raw_px);
    int64_t qty   = raw_qty;

    // security_id field is ASCII numeric
    uint32_t sec_id = static_cast<uint32_t>(std::atoi(snap.security_id));

    if (snap.md_entry_type == 0 || snap.md_entry_type == 1) {
        // Bid or Offer — emit a quote
        QuoteEvent ev{};
        ev.timestamp_ns = snap.transact_time;
        ev.security_id  = sec_id;
        std::memcpy(ev.symbol, snap.symbol, sizeof(ev.symbol));

        if (snap.md_entry_type == 0) { ev.bid = price; ev.bid_qty = qty; }
        else                         { ev.ask = price; ev.ask_qty = qty; }

        if (on_quote_) on_quote_(ev);
    } else if (snap.md_entry_type == 2) {
        // Trade
        TradeEvent ev{};
        ev.timestamp_ns  = snap.transact_time;
        ev.security_id   = sec_id;
        ev.price         = price;
        ev.qty           = qty;
        ev.aggressor_side = 'U';
        std::memcpy(ev.symbol, snap.symbol, sizeof(ev.symbol));

        if (on_trade_) on_trade_(ev);
    }
}

void UMDFParser::handle_incremental(const uint8_t* body, uint16_t size) {
    if (size < sizeof(MDIncrementalRefresh)) return;

    MDIncrementalRefresh hdr{};
    std::memcpy(&hdr, body, sizeof(hdr));
    hdr.transact_time = be64toh(hdr.transact_time);

    const uint8_t* cursor = body + sizeof(MDIncrementalRefresh);
    const uint8_t* end    = body + size;

    while (cursor + sizeof(MDEntry) <= end) {
        MDEntry entry{};
        std::memcpy(&entry, cursor, sizeof(entry));

        entry.md_update_action = static_cast<int32_t>(ntohl(static_cast<uint32_t>(entry.md_update_action)));
        entry.md_entry_type    = static_cast<int32_t>(ntohl(static_cast<uint32_t>(entry.md_entry_type)));
        entry.security_id      = ntohl(entry.security_id);
        entry.transact_time    = be64toh(entry.transact_time);

        int64_t raw_px;
        std::memcpy(&raw_px, &entry.md_entry_px, sizeof(raw_px));
        raw_px = static_cast<int64_t>(be64toh(static_cast<uint64_t>(raw_px)));

        int64_t raw_qty;
        std::memcpy(&raw_qty, &entry.md_entry_size, sizeof(raw_qty));
        raw_qty = static_cast<int64_t>(be64toh(static_cast<uint64_t>(raw_qty)));

        double  price = price8_to_double(raw_px);
        int64_t qty   = raw_qty;

        if (entry.md_entry_type == 0 || entry.md_entry_type == 1) {
            QuoteEvent ev{};
            ev.timestamp_ns = entry.transact_time;
            ev.security_id  = entry.security_id;
            if (entry.md_entry_type == 0) { ev.bid = price; ev.bid_qty = qty; }
            else                          { ev.ask = price; ev.ask_qty = qty; }
            if (on_quote_) on_quote_(ev);
        } else if (entry.md_entry_type == 2) {
            TradeEvent ev{};
            ev.timestamp_ns  = entry.transact_time;
            ev.security_id   = entry.security_id;
            ev.price         = price;
            ev.qty           = qty;
            ev.aggressor_side = (entry.md_update_action == 0) ? 'B' : 'S';
            if (on_trade_) on_trade_(ev);
        }

        cursor += sizeof(MDEntry);
    }
}

} // namespace b3
