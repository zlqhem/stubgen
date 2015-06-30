#include "api.h"


void api1(int x)
{
	puts ("calls api1\n");
}

int api1_pStructtype(mystruct *param_struct)
{
	return 0;
}

int api1_structtype(mystruct param_struct)
{
	return 0;
}
