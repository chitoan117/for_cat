#include "behavior_shadow.h"
#include <cmath>
#include <iomanip>
#include <initializer_list>
#include <locale>
#include <map>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace behavior_shadow {
namespace {
// Deliberately bounded config reader. No dependencies or permissive coercions.
// Only the JSON types used by this schema are accepted (arrays are not used).
struct Json {
    enum class Type { Null, Boolean, Number, String, Object } type = Type::Null;
    bool boolean = false;
    double number = 0;
    std::string text;
    std::map<std::string, Json> fields;
};
[[noreturn]] void bad(const std::string& message) { throw std::invalid_argument("shadow config: " + message); }
class Reader {
public:
    explicit Reader(const std::string& input) : input_(input) {
        if (input.size() > 65536) bad("input exceeds 64 KiB");
    }
    Json read() {
        Json result = value(0); whitespace();
        if (position_ != input_.size()) bad("trailing content");
        return result;
    }
private:
    const std::string& input_;
    std::size_t position_ = 0, nodes_ = 0;
    char peek() const { return position_ < input_.size() ? input_[position_] : '\0'; }
    char take() { if (position_ == input_.size()) bad("unexpected end"); return input_[position_++]; }
    void whitespace() { while (peek() == ' ' || peek() == '\t' || peek() == '\r' || peek() == '\n') ++position_; }
    void expect(char c) { if (take() != c) bad("unexpected token"); }
    void literal(const char* word) { while (*word) if (take() != *word++) bad("invalid literal"); }
    unsigned hex4() {
        unsigned result = 0;
        for (int i = 0; i < 4; ++i) {
            const char c = take();
            unsigned digit = 0;
            if (c >= '0' && c <= '9') digit = static_cast<unsigned>(c - '0');
            else if (c >= 'a' && c <= 'f') digit = static_cast<unsigned>(c - 'a') + 10;
            else if (c >= 'A' && c <= 'F') digit = static_cast<unsigned>(c - 'A') + 10;
            else bad("invalid Unicode escape");
            result = result * 16 + digit;
        }
        return result;
    }
    static void utf8(std::string& out, unsigned code) {
        if (code <= 0x7f) out += static_cast<char>(code);
        else if (code <= 0x7ff) {
            out += static_cast<char>(0xc0u | (code >> 6)); out += static_cast<char>(0x80u | (code & 63u));
        } else if (code <= 0xffff) {
            out += static_cast<char>(0xe0u | (code >> 12)); out += static_cast<char>(0x80u | ((code >> 6) & 63u));
            out += static_cast<char>(0x80u | (code & 63u));
        } else {
            out += static_cast<char>(0xf0u | (code >> 18)); out += static_cast<char>(0x80u | ((code >> 12) & 63u));
            out += static_cast<char>(0x80u | ((code >> 6) & 63u)); out += static_cast<char>(0x80u | (code & 63u));
        }
    }
    std::string string() {
        expect('"'); std::string out;
        while (peek() != '"') {
            const auto c = static_cast<unsigned char>(take());
            if (c < 0x20) bad("control character in string");
            if (c == '\\') {
                switch (take()) {
                case '"': out += '"'; break; case '\\': out += '\\'; break; case '/': out += '/'; break;
                case 'b': out += '\b'; break; case 'f': out += '\f'; break;
                case 'n': out += '\n'; break; case 'r': out += '\r'; break; case 't': out += '\t'; break;
                case 'u': {
                    unsigned code = hex4();
                    if (code >= 0xd800 && code <= 0xdbff) {
                        expect('\\'); expect('u'); const unsigned low = hex4();
                        if (low < 0xdc00 || low > 0xdfff) bad("invalid surrogate pair");
                        code = 0x10000 + ((code - 0xd800) << 10) + low - 0xdc00;
                    } else if (code >= 0xdc00 && code <= 0xdfff) bad("unpaired surrogate");
                    utf8(out, code); break;
                }
                default: bad("invalid string escape");
                }
            } else if (c < 0x80) out += static_cast<char>(c);
            else {
                unsigned code = 0, length = 0, minimum = 0;
                if (c >= 0xc2 && c <= 0xdf) { code = c & 31u; length = 1; minimum = 0x80; }
                else if (c >= 0xe0 && c <= 0xef) { code = c & 15u; length = 2; minimum = 0x800; }
                else if (c >= 0xf0 && c <= 0xf4) { code = c & 7u; length = 3; minimum = 0x10000; }
                else bad("invalid UTF-8");
                for (unsigned i = 0; i < length; ++i) {
                    const auto next = static_cast<unsigned char>(take());
                    if ((next & 0xc0u) != 0x80u) bad("invalid UTF-8 continuation");
                    code = (code << 6) | (next & 63u);
                }
                if (code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff)) bad("invalid UTF-8 codepoint");
                utf8(out, code);
            }
            if (out.size() > 4096) bad("string budget exceeded");
        }
        expect('"'); return out;
    }
    Json number() {
        const std::size_t start = position_;
        if (peek() == '-') ++position_;
        if (peek() == '0') ++position_;
        else { if (peek() < '1' || peek() > '9') bad("invalid number"); digits(); }
        if (peek() == '.') { ++position_; digits(); }
        if (peek() == 'e' || peek() == 'E') {
            ++position_; if (peek() == '+' || peek() == '-') ++position_; digits();
        }
        std::istringstream stream(input_.substr(start, position_ - start));
        stream.imbue(std::locale::classic());
        Json out; out.type = Json::Type::Number; stream >> out.number;
        if (!stream || !stream.eof() || !std::isfinite(out.number)) bad("non-finite/out-of-range number");
        return out;
    }
    void digits() {
        if (peek() < '0' || peek() > '9') bad("expected decimal digit");
        while (peek() >= '0' && peek() <= '9') ++position_;
    }
    Json value(unsigned depth) {
        if (depth > 16 || ++nodes_ > 2048) bad("nesting/node budget exceeded");
        whitespace(); Json out;
        switch (peek()) {
        case '{': {
            ++position_; out.type = Json::Type::Object; whitespace();
            if (peek() == '}') { ++position_; return out; }
            while (true) {
                whitespace(); const std::string key = string(); whitespace(); expect(':');
                if (!out.fields.emplace(key, value(depth + 1)).second) bad("duplicate key: " + key);
                whitespace(); if (peek() == '}') { ++position_; break; }
                expect(',');
            }
            break;
        }
        case '"': out.type = Json::Type::String; out.text = string(); break;
        case 'n': literal("null"); break;
        case 't': literal("true"); out.type = Json::Type::Boolean; out.boolean = true; break;
        case 'f': literal("false"); out.type = Json::Type::Boolean; break;
        default: out = number();
        }
        return out;
    }
};
void keys(const Json& object, std::initializer_list<const char*> allowed) {
    if (object.type != Json::Type::Object) bad("expected object");
    for (const auto& entry : object.fields) {
        bool found = false;
        for (const char* key : allowed) if (entry.first == key) found = true;
        if (!found) bad("unknown field: " + entry.first);
    }
}
const Json& field(const Json& object, const char* key) {
    if (object.type != Json::Type::Object) bad("expected object");
    const auto it = object.fields.find(key);
    if (it == object.fields.end()) bad(std::string("missing field: ") + key);
    return it->second;
}
std::string text(const Json& object, const char* key) {
    const auto& j = field(object, key); if (j.type != Json::Type::String) bad(std::string("expected string: ") + key);
    return j.text;
}
double numeric(const Json& object, const char* key) {
    const auto& j = field(object, key); if (j.type != Json::Type::Number) bad(std::string("expected number: ") + key);
    return j.number;
}
Millis integer(const Json& object, const char* key, Millis low, Millis high) {
    const double n = numeric(object, key);
    if (std::floor(n) != n || n < static_cast<double>(low) || n > static_cast<double>(high))
        bad(std::string("integer out of range: ") + key);
    return static_cast<Millis>(n);
}
void fixed(const Json& j, const char* key, const char* expected) {
    if (text(j,key) != expected) bad(std::string("invalid convention: ") + key);
}
Box box(const Json& j) {
    keys(j,{"x1","y1","x2","y2"});
    return {numeric(j,"x1"),numeric(j,"y1"),numeric(j,"x2"),numeric(j,"y2")};
}
std::string quote(const std::string& text_value) {
    std::ostringstream out; out.imbue(std::locale::classic()); out << '"';
    for (char raw : text_value) {
        const auto c = static_cast<unsigned char>(raw);
        if (c == '"' || c == '\\') out << '\\' << static_cast<char>(c);
        else if (c < 0x20) out << "\\u00" << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned>(c) << std::dec;
        else out << static_cast<char>(c);
    }
    out << '"'; return out.str();
}
} // namespace

Config load_config_json(const std::string& json, bool allow_synthetic) {
    const Json root = Reader(json).read();
    keys(root,{"schema_version","status","coordinate_system","food_bowl_color","water_bowl_color",
               "approach_reference","food_roi","water_roi","approach_line","tracker","geometry","temporal","notes"});
    if (integer(root,"schema_version",2,2) != 2) bad("unsupported schema");
    const auto status = text(root,"status");
    if (status != "CONFIGURED" && !(allow_synthetic && status == "SYNTHETIC_TEST_ONLY"))
        bad("configuration is not measured/configured; synthetic fixture needs explicit opt-in");
    fixed(root,"coordinate_system","normalized_original_camera_frame");
    fixed(root,"food_bowl_color","RED"); fixed(root,"water_bowl_color","BLUE");
    fixed(root,"approach_reference","BLUE_FLOOR_LINE");
    if (root.fields.count("notes") != 0) static_cast<void>(text(root,"notes"));
    Config c; c.geometry.food_roi = box(field(root,"food_roi")); c.geometry.water_roi = box(field(root,"water_roi"));
    const auto& line = field(root,"approach_line");
    if (line.type != Json::Type::Null) {
        const Box coordinates = box(line); // endpoints, not a positive-area rectangle
        c.geometry.approach_line_start = Maybe<Point>({coordinates.x1, coordinates.y1});
        c.geometry.approach_line_end = Maybe<Point>({coordinates.x2, coordinates.y2});
    }
    const auto& tr = field(root,"tracker");
    keys(tr,{"min_confidence","min_iou","max_centroid_distance","ttl_ms","history_capacity"});
    c.tracker.min_confidence = numeric(tr,"min_confidence"); c.tracker.min_iou = numeric(tr,"min_iou");
    c.tracker.max_centroid_distance = numeric(tr,"max_centroid_distance"); c.tracker.ttl_ms = integer(tr,"ttl_ms",1,600000);
    c.tracker.history_capacity = static_cast<std::size_t>(integer(tr,"history_capacity",2,512));
    const auto& g = field(root,"geometry");
    keys(g,{"near_distance","exit_distance","min_body_overlap","min_motion_per_second","motion_window_ms"});
    c.geometry.near_distance = numeric(g,"near_distance"); c.geometry.exit_distance = numeric(g,"exit_distance");
    c.geometry.min_body_overlap = numeric(g,"min_body_overlap");
    c.geometry.min_motion_per_second = numeric(g,"min_motion_per_second"); c.geometry.motion_window_ms = integer(g,"motion_window_ms",1,600000);
    const auto& t = field(root,"temporal");
    keys(t,{"confirm_ms","dropout_ms","min_state_ms","max_observation_gap_ms","max_behavior_age_ms","min_behavior_confidence"});
    c.temporal.confirm_ms = integer(t,"confirm_ms",1,600000); c.temporal.dropout_ms = integer(t,"dropout_ms",1,600000);
    c.temporal.min_state_ms = integer(t,"min_state_ms",1,600000);
    c.temporal.max_observation_gap_ms = integer(t,"max_observation_gap_ms",1,600000);
    c.temporal.max_behavior_age_ms = integer(t,"max_behavior_age_ms",1,600000);
    c.temporal.min_behavior_confidence = numeric(t,"min_behavior_confidence");
    validate_config(c); return c;
}

std::string event_json(const Event& e) {
    if (!e.shadow_only || e.weight_before.present || e.weight_after.present || e.consumed_grams.present)
        throw std::invalid_argument("only shadow events with unbound weight hooks can be serialized");
    std::ostringstream out; out.imbue(std::locale::classic()); out << std::setprecision(17);
    out << "{\"schema_version\":1,\"event_type\":" << quote(name(e.type))
        << ",\"shadow_only\":true,\"clock\":\"monotonic_ms\",\"track_id\":" << e.track_id
        << ",\"session_id\":" << e.session_id << ",\"emitted_ms\":" << e.emitted_ms << ",\"start_ms\":" << e.start_ms
        << ",\"end_ms\":" << (e.end_ms.present ? std::to_string(e.end_ms.value) : "null")
        << ",\"duration_ms\":" << (e.duration_ms.present ? std::to_string(e.duration_ms.value) : "null")
        << ",\"roi\":" << quote(name(e.roi)) << ",\"reason\":" << quote(name(e.reason))
        << ",\"geometry_reference\":\"bbox_bottom_center_and_body_overlap\",\"confidence\":{\"samples\":" << e.confidence.samples
        << ",\"mean\":" << e.confidence.mean << ",\"min\":" << e.confidence.minimum << ",\"max\":" << e.confidence.maximum << "}"
        << ",\"weight_before\":null,\"weight_after\":null,\"consumed_grams\":null"
        << ",\"trial_id\":" << (e.metadata.trial_id.empty() ? "null" : quote(e.metadata.trial_id))
        << ",\"food_id\":" << (e.metadata.food_id.empty() ? "null" : quote(e.metadata.food_id)) << '}';
    return out.str();
}
} // namespace behavior_shadow
