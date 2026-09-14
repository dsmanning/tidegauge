#ifndef TIDEGAUGE_NONCE_STORAGE_H
#define TIDEGAUGE_NONCE_STORAGE_H
#include <LittleFS.h>
#include "../app/join_nonce.h"
namespace tidegauge {
class LittleFsNonceStorage : public NonceStorage {
public:
    void set_ready(bool ready) {ready_=ready;}
    bool load(uint32_t& high) override {
        if(!ready_) return false;
        if(!LittleFS.exists("/join-nonce.bin")) {high=0; return true;}
        return read("/join-nonce.bin",high);
    }
    bool save(uint32_t high) override {
        if(!ready_ || high>65536) return false;
        uint8_t bytes[12]; encode_nonce_record(high,bytes);
        auto file=LittleFS.open("/join-nonce.pending","w");
        if(!file) return false;
        const bool written=file.write(bytes,sizeof(bytes))==sizeof(bytes);
        file.flush(); file.close();
        uint32_t verified;
        if(!written || !read("/join-nonce.pending",verified) || verified!=high) return false;
        // LittleFS rename atomically replaces the committed reservation.
        if(!LittleFS.rename("/join-nonce.pending","/join-nonce.bin")) return false;
        return read("/join-nonce.bin",verified) && verified==high;
    }
private:
    bool read(const char* path,uint32_t& high) {
        auto file=LittleFS.open(path,"r");
        if(!file) return false;
        uint8_t bytes[12];
        const bool ok=file.size()==sizeof(bytes) && file.read(bytes,sizeof(bytes))==sizeof(bytes);
        file.close(); return ok && decode_nonce_record(bytes,high);
    }
    bool ready_=false;
};
}
#endif
