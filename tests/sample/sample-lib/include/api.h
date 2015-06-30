#ifndef _API_H_
#define _API_H_

extern void api1(int x);
extern void api2(int x);
extern void api3(int x);

struct field {
	int int_field_x;
};

typedef struct _mystruct {
	int int_x;
	struct field myfield;
} mystruct;

#endif

