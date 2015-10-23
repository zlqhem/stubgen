CC := gcc
AR := ar

SRCS := src/api1.c src/api2.c src/api3.c
OBJS := $(SRCS:%.c=%.o) 
DWARFLOG := $(SRCS:%.c=%.dwarf)

TARGET := libmyapi.so

all: $(TARGET) $(DWARFLOG) libmyapi.a

$(TARGET): $(OBJS)
	$(CC) -shared -Wl,-soname,$@.1 -g -o $@ $^
	readelf -w $@ > $@.dwarf

libmyapi.a: $(OBJS) 
	$(AR) -rcs $@ $^
	readelf -w $@ > $@.dwarf

%.o: %.c
	$(CC) -c -fPIC -g -o $@ $< -Iinclude

%.dwarf: %.o
	readelf -w $< > $@

clean:
	-rm $(OBJS) $(TARGET) libmyapi.a $(DWARFLOG)
