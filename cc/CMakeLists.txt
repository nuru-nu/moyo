CMAKE_MINIMUM_REQUIRED(VERSION 3.8)
SET(CMAKE_CXX_STANDARD 11)
SET(CMAKE_CXX_STANDARD_REQUIRED True)

PROJECT(nuru)

FIND_PACKAGE(OpenCV REQUIRED)
INCLUDE_DIRECTORIES(${OpenCV_INCLUDE_DIRS})
LIST(APPEND EXTRA_LIBS ${OpenCV_LIBS})

FIND_PACKAGE(freenect2 REQUIRED)
INCLUDE_DIRECTORIES(${freenect2_INCLUDE_DIRS})
LIST(APPEND EXTRA_LIBS ${freenect2_LIBRARIES})

add_definitions(-DBOOST_ERROR_CODE_HEADER_ONLY)

# *************************************
# OpenNI 2

OPTION (ENABLE_OPENNI2_NITE2 ON)

IF( ENABLE_OPENNI2_NITE2 )
set(OPENNI2_DEFINITIONS ${PC_OPENNI_CFLAGS_OTHER})

FIND_LIBRARY( OPENNI2_LIBRARY
             NAMES OpenNI2
             HINTS ${PC_OPENNI2_LIBDIR} ${PC_OPENNI2_LIBRARY_DIRS} /usr/lib
             PATHS "$ENV{PROGRAMFILES}/OpenNI2/Lib${OPENNI2_SUFFIX}"    "$ENV{PROGRAMW6432}/OpenNI2/Lib${OPENNI2_SUFFIX}" "$ENV{PROGRAMW6432}/OpenNI2"
             PATH_SUFFIXES lib lib64
)
FIND_PATH( OPENNI2_INCLUDE_DIR OpenNI.h
             HINTS ${PC_OPENNI2_INCLUDEDIR} ${PC_OPENNI2_INCLUDE_DIRS} 
             /usr/include/openni2 /usr/include/ni2
             PATHS "$ENV{PROGRAMFILES}/OpenNI2/include" "$ENV{PROGRAMW6432}/OpenNI2/include"
)
LIST(APPEND EXTRA_LIBS  ${OPENNI2_LIBRARY})


FIND_LIBRARY( NITE2_LIBRARY
             NAMES NiTE2
             HINTS ${HOME}/git/NiTE-Linux-x64-2.2/Redist
             PATHS "${HOME}/git/NiTE-Linux-x64-2.2/Redist"
)

FIND_PATH( NITE2_INCLUDE_DIR NiTE.h
      HINTS ${HOME}/git/NiTE-Linux-x64-2.2/Include
      PATHS "${HOME}/git/NiTE-Linux-x64-2.2/Include"
)
LIST(APPEND EXTRA_LIBS  ${NITE2_LIBRARY} )
ENDIF( ENABLE_OPENNI2_NITE2 )

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(OpenNI2 DEFAULT_MSG
    OPENNI2_LIBRARY OPENNI2_INCLUDE_DIR)

mark_as_advanced(OPENNI2_LIBRARY OPENNI2_INCLUDE_DIR)

if (OPENNI2_FOUND)
    INCLUDE_DIRECTORIES( ${OPENNI2_INCLUDE_DIR} ${NITE2_INCLUDE_DIR} )
    message (STATUS "OpenNI2 found (include: ${OPENNI2_INCLUDE_DIR}, lib: ${OPENNI2_LIBRARY})")
link_directories( ${OPENNI2_LIBRARY} ${NITE2_LIBRARY})
endif (OPENNI2_FOUND)

# *************************************
# PCL

find_package(PCL 1.8 REQUIRED COMPONENTS common io)

if( PCL_FOUND )
  include_directories( ${PCL_INCLUDE_DIRS} )
  link_directories( ${PCL_LIBRARY_DIRS} )
  add_definitions( ${PCL_DEFINITIONS} )
endif()

LIST(APPEND EXTRA_LIBS  ${PCL_LIBRARIES} )
# *************************************


ADD_EXECUTABLE(kinect features.cc hardware.cc kinect.cc network.cc util.cc viewer.cc)
# ADD_EXECUTABLE(kinect kinect.cc)
TARGET_LINK_LIBRARIES(kinect PUBLIC ${EXTRA_LIBS})

# ADD_EXECUTABLE(test_ test.cc)
# TARGET_LINK_LIBRARIES(test_ PUBLIC ${EXTRA_LIBS})
