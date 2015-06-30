CC := gcc
AR := ar

SRCS := src/api1.c src/api2.c src/api3.c
OBJS := $(SRCS:%.c=%.o) 
ELFLOG := $(SRCS:%.c=%.elf)

TARGET := libmyapi.a

all: $(TARGET) $(ELFLOG)

$(TARGET): $(OBJS) 
	$(AR) -rcs $@ $^

%.o: %.c
	$(CC) -c -fPIC -g -o $@ $< -Iinclude

%.elf: %.o
	readelf -w $< > $@

clean:
	-rm $(OBJS) $(TARGET) $(ELFLOG)
