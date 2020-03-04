#ifndef SMANMI_UTIL_H
#define SMANMI_UTIL_H

#include <string>
#include <memory>

#include <sys/time.h>
#include <time.h>
#include <math.h>

template<typename ... Args>
std::string string_format( const std::string& format, Args ... args )
{
  size_t size = snprintf( nullptr, 0, format.c_str(), args ... ) + 1; // Extra space for '\0'
  if( size <= 0 ){ throw std::runtime_error( "Error during formatting." ); }
  std::unique_ptr<char[]> buf( new char[ size ] ); 
  snprintf( buf.get(), size, format.c_str(), args ... );
  return std::string( buf.get(), buf.get() + size - 1 ); // We don't want the '\0' inside
}

std::string datetime_str();

// std::string datetime_str(){
//   char buffer[26];
//   int millisec;
//   struct tm* tm_info;
//   struct timeval tv;

//   gettimeofday(&tv, NULL);

//   millisec = lrint(tv.tv_usec/1000.0); // Round to nearest millisec
//   if (millisec>=1000) { // Allow for rounding up to nearest second
//     millisec -=1000;
//     tv.tv_sec++;
//   }

//   tm_info = localtime(&tv.tv_sec);

//   strftime(buffer, 26, "%Y:%m:%d_%H:%M:%S", tm_info);
//   std::string dt_string = buffer;

//   return dt_string + ":" + std::to_string(millisec);
// }

#endif
