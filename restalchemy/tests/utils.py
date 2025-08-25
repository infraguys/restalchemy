def make_test_name(testcase_func, param_num, param):
    """
    Generic name function for parameterized tests
    Example:
        test_smth_1_arg1.1_arg2.1
        test_smth_2_arg1.2_arg2.1
        test_smth_3_arg1.3_arg2.1
                  ^^^^^^^^^^^^^^^
    """
    params_str = "_".join(str(i).replace(" ", "_") for i in param[0])
    return f"{testcase_func.__name__}_{param_num}_{params_str}"
