#ifndef SMANMI_SETTINGS_H
#define SMANMI_SETTINGS_H


struct person_t {

    int id;
    float cm[3];   // 3D center of mass point
} ;

using Values = std::map<std::string, float>;


#endif