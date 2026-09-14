#ifndef TIDEGAUGE_JOIN_NONCE_H
#define TIDEGAUGE_JOIN_NONCE_H
#include <cstdint>
namespace tidegauge {
inline void encode_nonce_record(uint32_t high, uint8_t bytes[12]) {
    const uint32_t words[3]={0x54474e31u,high,~high};
    for(unsigned w=0;w<3;++w) for(unsigned b=0;b<4;++b) bytes[w*4+b]=words[w]>>(24-b*8);
}
inline bool decode_nonce_record(const uint8_t bytes[12], uint32_t& high) {
    uint32_t words[3]{};
    for(unsigned w=0;w<3;++w) for(unsigned b=0;b<4;++b) words[w]=(words[w]<<8)|bytes[w*4+b];
    high=words[1];
    return words[0]==0x54474e31u && high<=65536 && words[2]==~high;
}
struct NonceStorage {
    virtual bool load(uint32_t& exclusive_high_water) = 0;
    virtual bool save(uint32_t exclusive_high_water) = 0;
    virtual ~NonceStorage() = default;
};
// Commit a range before using it. A reset may skip numbers, never reuse them.
class JoinNonce {
public:
    explicit JoinNonce(NonceStorage& storage) : storage_(storage) {}
    bool next(uint16_t& nonce) {
        if (failed_) return false;
        if (!loaded_) {
            if (!storage_.load(next_) || next_ > 65536) {failed_=true; return false;}
            end_=next_; loaded_=true;
        }
        if (next_==end_) {
            if (next_>=65536) return false;
            const uint32_t end=next_+32>65536 ? 65536 : next_+32;
            if (!storage_.save(end)) {failed_=true; return false;}
            end_=end;
        }
        nonce=static_cast<uint16_t>(next_++); return true;
    }
private:
    NonceStorage& storage_; uint32_t next_=0, end_=0; bool loaded_=false, failed_=false;
};
}
#endif
