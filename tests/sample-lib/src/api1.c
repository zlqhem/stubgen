#include "api.h"


static int static_function_should_not_be_identified_as_stub_target(int x)
{
	return 0;
}

void api1(int x)
{
	puts ("calls api1\n");
}

void api1_constparam(const int* pc_x)
{
	puts ("calls api1_constparam\n");
}

int api1_pStructtype(mystruct *param_struct)
{
	return 0;
}

int api1_structtype(mystruct param_struct)
{
	return 0;
}

void api1_time(time_t *timer)
{
	time(timer);
}

struct tm g_tm;
struct tm api1_tm(struct tm arg_tm)
{
	return g_tm;
}

// case 1. returns pointer to struct
struct tm* api1_return_ptr_struct_tm()
{
	return &g_tm;
}

// case 2. returns pointer to typedef 
typedef struct tm t_tm;
t_tm* api1_return_ptr_typedef_tm()
{
	return (t_tm*)0;
}

// case 3. returns typedef of non-pointer type
t_tm api_return_typedef_of_non_pointer()
{
	t_tm ret;
	return ret;
}
// case 4. returns function pointer
typedef int (*MyFunction) (int);

int dummy(int x)
{
	return 0;
}

MyFunction api1_return_pfn(int x)
{
	return dummy;
}

/* Should generate the following code :
   XXX = api1_return_pfn
   prototype = MyFunction api1_return_pfn(int)

#1. typedef callback: STUBGEN_XXX_CALLBACK
typedef MyFunction (*STUBGEN_api1_return_pfn_CALLBACK)(int, int);

#2. variable declaration of callback pointer:
static STUBGEN_api1_return_pfn_CALLBACK 
	s_callback_api1_return_pfn = 0;

#3-1. define stub setter: void XXX_StubWithCallback(STUBGEN_XXX_CALLBACK)
void api_return_pfn_StubWithCallback(STUBGEN_api1_return_pfn_CALLBACK cb)
{
	s_callback_api1_return_pfn = cb;
}

#3-2. define XXX_StubReturns
void api_return_pfn_StubReturns(MyFunction ret)
{
	???
}

#4-1. define dummy returns specified type
MyFunction default_value_MyFunction()
{
	MyFunction temp = {0, };
	return temp;
}

# e.g) for struct UserType { int x; int y;} 
UserType default_value_UserType()
{
	UserType temp = {0, };
	return temp;
}

#4-2. define stub function: 
MyFunction api1_return_pfn(int x)
{
	if (s_callback_api1_return_pfn) {
		static int cnt = 0;
		return s_callback_api1_return_pfn(x, cnt);

	}
	// return default_value_<TYPE>();
	// e.g) return default_value_int();
	return default_value_MyFunction();
}
*/
