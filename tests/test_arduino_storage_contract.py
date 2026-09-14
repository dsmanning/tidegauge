import subprocess
from pathlib import Path


def test_atomic_nonce_storage_keeps_committed_high_water_on_write_failure(tmp_path):
    (tmp_path / 'LittleFS.h').write_text('''
#pragma once
#include <map>
#include <string>
#include <vector>
#include <cstdint>
#include <cstring>
inline bool write_ok=true, rename_ok=true;
struct File {
 std::vector<uint8_t>* v=nullptr;
 operator bool()const{return v!=nullptr;}
 size_t size(){return v->size();}
 size_t read(uint8_t* b,size_t n){if(v->size()<n)return 0; memcpy(b,v->data(),n);return n;}
 size_t write(const uint8_t* b,size_t n){if(!write_ok)return 0; v->assign(b,b+n);return n;}
 void flush(){} void close(){}
};
struct FS {
 std::map<std::string,std::vector<uint8_t>> files;
 bool exists(const char* p){return files.count(p);}
 File open(const char* p,const char* mode){
  if(*mode=='w'){files[p].clear();return {&files[p]};}
  return exists(p) ? File{&files[p]} : File{};
 }
 bool rename(const char* a,const char* b){if(!rename_ok)return false; files[b]=files[a];files.erase(a);return true;}
};
inline FS LittleFS;
''')
    source=tmp_path/'main.cpp'
    source.write_text('''
#include <cassert>
#include "src/adapters/nonce_storage.h"
int main(){
 tidegauge::LittleFsNonceStorage s; uint32_t high;
 assert(!s.load(high)); s.set_ready(true);
 assert(s.load(high) && high==0);
 assert(s.save(32)); assert(s.load(high) && high==32);
 write_ok=false; assert(!s.save(64)); assert(s.load(high) && high==32);
 write_ok=true; rename_ok=false;
 assert(!s.save(64)); assert(s.load(high) && high==32);
 rename_ok=true; assert(s.save(64)); assert(s.load(high) && high==64);
 LittleFS.files["/join-nonce.bin"][5]^=1;
 assert(!s.load(high));
}
''')
    root=Path(__file__).resolve().parents[1]/'arduino/ttn_otaa_lmic'
    binary=tmp_path/'test'
    result=subprocess.run(['g++','-std=c++17','-I',str(tmp_path),'-I',str(root),str(source),'-o',str(binary)],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    subprocess.run([str(binary)],check=True,timeout=5)
