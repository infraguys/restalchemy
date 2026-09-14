# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/infraguys/restalchemy/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                           |    Stmts |     Miss |   Branch |   BrPart |   Cover |   Missing |
|--------------------------------------------------------------- | -------: | -------: | -------: | -------: | ------: | --------: |
| restalchemy/\_\_init\_\_.py                                    |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/api/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/api/actions.py                                     |       51 |       12 |        8 |        2 |     73% |38-40, 43-44, 55-56, 59-60, 69, 78, 90 |
| restalchemy/api/applications.py                                |       38 |        0 |        2 |        1 |     98% | 54-\>exit |
| restalchemy/api/constants.py                                   |       17 |        0 |        0 |        0 |    100% |           |
| restalchemy/api/contexts.py                                    |       41 |        3 |        4 |        1 |     91% |55, 78, 87 |
| restalchemy/api/controllers.py                                 |      499 |       25 |      140 |       12 |     94% |208-212, 259, 293, 409, 412, 430, 476, 489, 539, 553, 556, 562, 565-568, 652-655, 885, 934, 1021, 1093 |
| restalchemy/api/field\_permissions.py                          |       68 |        3 |       20 |        3 |     93% |151, 155, 218 |
| restalchemy/api/filter\_lang.py                                |      398 |       12 |      142 |       10 |     96% |196, 199, 270, 291, 394, 474, 537, 600, 602, 604, 619, 682 |
| restalchemy/api/middlewares/\_\_init\_\_.py                    |       29 |       11 |        4 |        1 |     58% |26-28, 33-36, 57, 61, 68-69, 74 |
| restalchemy/api/middlewares/contexts.py                        |       41 |        0 |       16 |        0 |    100% |           |
| restalchemy/api/middlewares/errors.py                          |       34 |        0 |       10 |        0 |    100% |           |
| restalchemy/api/middlewares/logging.py                         |       70 |        7 |       20 |        3 |     89% |38-\>40, 60, 74-87, 135 |
| restalchemy/api/middlewares/metrics.py                         |       27 |       27 |        4 |        0 |      0% |     18-64 |
| restalchemy/api/middlewares/retry\_on\_error.py                |       18 |        0 |        2 |        0 |    100% |           |
| restalchemy/api/packers.py                                     |      185 |        8 |       68 |        6 |     94% |141-\>149, 206, 259, 292-294, 367, 372, 389-391 |
| restalchemy/api/resources.py                                   |      373 |       19 |       72 |       11 |     93% |42, 50, 96, 106-107, 213, 216, 305, 321, 522, 533, 598, 649, 701, 799, 828, 836, 860-861 |
| restalchemy/api/routes.py                                      |      427 |       19 |      164 |       13 |     95% |80-\>92, 94-\>106, 101-\>95, 125, 131-132, 141, 191, 207-208, 278, 358, 423-424, 530, 537, 603, 624, 630, 654, 667, 688 |
| restalchemy/cmd/\_\_init\_\_.py                                |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/cmd/apply\_migration.py                            |       18 |       18 |        0 |        0 |      0% |     17-66 |
| restalchemy/cmd/new\_migration.py                              |       16 |       16 |        2 |        0 |      0% |     17-68 |
| restalchemy/cmd/rename\_migrations.py                          |       40 |       40 |        8 |        0 |      0% |     17-98 |
| restalchemy/cmd/rollback\_migration.py                         |       17 |       17 |        0 |        0 |      0% |     17-57 |
| restalchemy/common/\_\_init\_\_.py                             |        6 |        3 |        2 |        0 |     38% |     22-24 |
| restalchemy/common/config.py                                   |       15 |       15 |        4 |        0 |      0% |     16-44 |
| restalchemy/common/config\_opts.py                             |       47 |       27 |        0 |        0 |     43% |302-324, 347, 378, 412-433, 459-480 |
| restalchemy/common/constants.py                                |       15 |        0 |        0 |        0 |    100% |           |
| restalchemy/common/contexts.py                                 |      126 |       34 |       18 |        0 |     68% |62-65, 223, 228, 239-241, 256-259, 274, 290-293, 318-322, 331, 342-345, 355-357, 372-374, 391-397, 412 |
| restalchemy/common/exceptions.py                               |      120 |        6 |        4 |        1 |     94% |150-152, 159, 162, 172 |
| restalchemy/common/log.py                                      |       19 |       19 |        4 |        0 |      0% |     18-76 |
| restalchemy/common/singletons.py                               |       11 |        0 |        4 |        1 |     93% |   35-\>37 |
| restalchemy/common/status.py                                   |       74 |        5 |        0 |        0 |     93% |19, 23, 27, 31, 35 |
| restalchemy/common/utils.py                                    |       47 |        2 |       10 |        1 |     95% |51, 57-\>63, 126 |
| restalchemy/dm/\_\_init\_\_.py                                 |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/dm/filters.py                                      |       62 |        0 |        4 |        0 |    100% |           |
| restalchemy/dm/models.py                                       |      252 |       23 |       60 |        6 |     88% |127-129, 132, 172, 207, 283, 290, 309, 345-348, 366-370, 408, 417-418, 426-429, 469 |
| restalchemy/dm/properties.py                                   |      343 |       22 |       98 |        0 |     92% |68, 227-234, 238, 323, 335, 458, 674, 677, 691-692, 715-719 |
| restalchemy/dm/relationships.py                                |       71 |       14 |       16 |        5 |     76% |25-26, 35-36, 40-41, 64-65, 71, 83, 93, 102, 113, 123 |
| restalchemy/dm/types.py                                        |      640 |      127 |      132 |       17 |     76% |99, 108, 164, 172, 185, 203, 214, 258, 260, 310, 335, 342, 351, 353, 360, 362, 368, 372, 387-390, 394-397, 400-411, 415-419, 452, 456-459, 463-466, 469-480, 484-488, 519, 528-534, 542-549, 553, 671, 678-686, 691, 721-729, 734, 739-744, 747, 752, 755-756, 759-769, 774, 844-\>852, 860, 869-\>871, 909-911, 914, 918-921, 925-928, 931-941, 945, 950, 953, 956, 959, 963, 986, 1005, 1008-1011, 1051, 1069, 1098, 1127, 1150, 1160, 1185-1186, 1187-\>1197, 1191-\>1197, 1201 |
| restalchemy/dm/types\_dynamic.py                               |      107 |       37 |       20 |        2 |     60% |47-57, 89, 125-126, 173-187, 203, 223-\>225, 259-264, 280-282, 305 |
| restalchemy/dm/types\_network.py                               |      133 |       20 |        8 |        1 |     85% |42, 45, 48, 51, 76, 79, 82, 85, 112, 115, 118, 121, 147, 163, 172, 179, 193, 216, 247, 277 |
| restalchemy/openapi/\_\_init\_\_.py                            |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/openapi/cache.py                                   |       50 |        1 |       12 |        1 |     97% |       133 |
| restalchemy/openapi/constants.py                               |       50 |        8 |        6 |        1 |     77% |223, 248-250, 269-276, 314-\>316 |
| restalchemy/openapi/engines.py                                 |       17 |        0 |        0 |        0 |    100% |           |
| restalchemy/openapi/impl303.py                                 |       24 |        1 |        0 |        0 |     96% |        88 |
| restalchemy/openapi/impl310.py                                 |       24 |        0 |        0 |        0 |    100% |           |
| restalchemy/openapi/parse.py                                   |       48 |        3 |       26 |        5 |     89% |32, 44-\>48, 56-\>60, 64, 88-\>115, 113 |
| restalchemy/openapi/structures.py                              |      182 |        0 |       44 |        7 |     97% |79-\>82, 143-\>146, 146-\>149, 149-\>151, 151-\>154, 344-\>342, 357-\>356 |
| restalchemy/openapi/utils.py                                   |      105 |       22 |       18 |        5 |     75% |90-\>92, 157-173, 199-209, 221, 223, 225 |
| restalchemy/storage/\_\_init\_\_.py                            |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/base.py                                    |       49 |        4 |        2 |        0 |     92% |     40-43 |
| restalchemy/storage/exceptions.py                              |       53 |        3 |        6 |        2 |     92% |54, 84, 104 |
| restalchemy/storage/sql/\_\_init\_\_.py                        |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/sql/constants.py                           |        3 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/sql/dialect/\_\_init\_\_.py                |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/sql/dialect/adapters.py                    |       20 |        3 |        6 |        0 |     81% |     61-65 |
| restalchemy/storage/sql/dialect/base.py                        |      199 |        7 |       32 |        2 |     94% |100-102, 129-130, 146-\>148, 398, 718 |
| restalchemy/storage/sql/dialect/exceptions.py                  |       11 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/sql/dialect/mysql.py                       |       66 |        4 |        4 |        0 |     94% |126, 142, 160, 364 |
| restalchemy/storage/sql/dialect/pgsql.py                       |       72 |        8 |        0 |        0 |     89% |53-56, 131, 149, 167, 365 |
| restalchemy/storage/sql/dialect/query\_builder/\_\_init\_\_.py |        0 |        0 |        0 |        0 |    100% |           |
| restalchemy/storage/sql/dialect/query\_builder/common.py       |       69 |        2 |        0 |        0 |     97% |   29, 105 |
| restalchemy/storage/sql/dialect/query\_builder/q.py            |      254 |        4 |       38 |        2 |     98% |35, 360-\>363, 412-417, 459 |
| restalchemy/storage/sql/engines.py                             |      195 |       12 |       32 |        4 |     93% |133, 393-\>396, 514-\>516, 533-538, 550-\>exit, 662, 708-709, 743-744 |
| restalchemy/storage/sql/filters.py                             |      204 |        8 |       40 |        2 |     96% |170, 239, 472, 475, 478, 481, 548, 554 |
| restalchemy/storage/sql/migrations.py                          |      237 |       26 |       70 |        7 |     87% |68, 72, 88, 94, 132-133, 216-\>214, 219, 220-\>214, 224, 249-250, 297, 339-356, 359 |
| restalchemy/storage/sql/orm.py                                 |      260 |       15 |       76 |        8 |     93% |126, 129-134, 137-146, 167-180, 257-\>259, 346-\>336, 395, 406, 499, 541-\>exit, 582 |
| restalchemy/storage/sql/sessions.py                            |      194 |       21 |       36 |        7 |     86% |63-74, 108-120, 139, 142-\>exit, 173-\>exit, 240, 243-\>exit, 277, 280-\>exit, 338-349 |
| restalchemy/storage/sql/tables.py                              |       87 |        3 |       28 |        3 |     95% |56-\>58, 92-\>94, 158, 177-186 |
| restalchemy/storage/sql/utils.py                               |       36 |        1 |        8 |        0 |     98% |        28 |
| restalchemy/version.py                                         |        2 |        2 |        0 |        0 |      0% |     15-17 |
| **TOTAL**                                                      | **7006** |  **749** | **1554** |  **153** | **88%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/infraguys/restalchemy/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/infraguys/restalchemy/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/infraguys/restalchemy/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/infraguys/restalchemy/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Finfraguys%2Frestalchemy%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/infraguys/restalchemy/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.