#!/usr/bin/python3
# Copyright (c) 2024 Espressif Systems (Shanghai) Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

import os
import sys
import yaml
import argparse
from pathlib import Path
from datetime import datetime

current_year = datetime.now().year

file_out_head = f'''/*
 * Copyright (c) {current_year} Espressif Systems (Shanghai) Co., Ltd.
 *
 * SPDX-License-Identifier: Apache-2.0
 *
 * NOTE: Autogenerated file using esp_genpinctrl.py
 */

#ifndef INC_DT_BINDS_PINCTRL_''' + '''{SOC}''' + '''_PINCTRL_HAL_H_
#define INC_DT_BINDS_PINCTRL_''' + '''{SOC}''' + '''_PINCTRL_HAL_H_

'''

file_out_tail = '''
#endif /* INC_DT_BINDS_PINCTRL_{SOC}_PINCTRL_HAL_H_ */
'''

file_out_path = 'include/zephyr/dt-bindings/pinctrl/'
file_out_temp = '{SOC}-pinctrl-temp.h'
file_out_name = '{SOC}-pinctrl.h'
file_tmp_abs = ''

line_comment = ''


def err(source, msg):
    global file_tmp_abs
    os.remove(file_tmp_abs)
    sys.exit('ERR(' + source + '):' + msg)


def get_pin_ios(pins):
    ios = []
    for io in pins:
        if type(io) is int:
            ios.append(io)
        elif type(io) is list and io.__len__() == 2:
            for io_num in range(io[0], 1 + io[1]):
                ios.append(io_num)
        else:
            err('gpio', 'bad type / wrong list size')

    return ios


def get_gpios(pin_info):
    if 'gpio' in pin_info:
        return get_pin_ios(pin_info.get('gpio'))
    else:
        err('gpio', 'missing property')


def get_pin_sigi(pin_info):
    sigi = 'ESP_'
    if 'sigi' in pin_info:
        sigi = sigi + pin_info['sigi'].upper()
    else:
        sigi = sigi + 'NOSIG'

    return sigi


def get_pin_sigo(pin_info):
    sigo = 'ESP_'
    if 'sigo' in pin_info:
        sigo = sigo + pin_info['sigo'].upper()
    else:
        sigo = sigo + 'NOSIG'

    return sigo


def get_pinmux(dev_name, pin_name, pin_info, io):
    sigi = get_pin_sigi(pin_info)
    sigo = get_pin_sigo(pin_info)
    global line_comment

    pinmux = dev_name.upper() + '_' + pin_name.upper() + '_GPIO' + str(io)
    define_str = '#define ' + pinmux
    macro_str = 'ESP32_PINMUX(' + str(io) + ', ' + sigi + ', ' + sigo + ')'

    if len(define_str + ' ' + macro_str) > 100:
        # print in two lines
        pinmux = define_str + ' \\\n\t' + macro_str + '\n\n'
    else:
        pinmux = define_str + ' ' + macro_str + '\n\n'

    if bool(line_comment):
        pinmux = line_comment + pinmux
        line_comment = ''

    return pinmux


def main(pcfg_in):
    zephyr_base = os.getenv('ZEPHYR_BASE')

    if zephyr_base is None:
        print("Missing ZEPHYR_BASE environment variable")
        exit()

    print("Zephyr Base: ", zephyr_base)

    stream = open(pcfg_in, 'r')
    pcfg_data = yaml.load(stream, Loader=yaml.FullLoader)
    soc = os.path.basename(pcfg_in).replace('.yml', '')

    file_out_abs = Path(zephyr_base, file_out_path + soc + '-pinctrl.h')
    global file_tmp_abs
    file_tmp_abs = Path(zephyr_base, file_out_path + soc + '-pinctrl-temp.h')

    # sorts by dev name, which keeps git
    # diffs minimal and easily trackable
    all_data = sorted(pcfg_data.items())

    f = open(file_tmp_abs, 'w')
    f.write(file_out_head.replace('{SOC}', soc.upper()))

    for (dev_name, dev_info) in all_data:

        # sorts by pin name, which keeps git
        # diffs minimal and easily trackable
        dev_info = sorted(dev_info.items())

        for (pin_name, pin_info) in dev_info:
            global line_comment
            line_comment = '/* ' + dev_name.upper() + '_' + pin_name.upper() + ' */\n'
            ios = get_gpios(pin_info)
            for io in ios:
                pinmux = get_pinmux(dev_name, pin_name, pin_info, io)
                f.write(pinmux)

    f.write(file_out_tail.replace('{SOC}', soc.upper()))
    f.close()

    if os.path.exists(file_out_abs):
        os.remove(file_out_abs)

    os.rename(file_tmp_abs, file_out_abs)

    print("Output file: ", file_out_abs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-p',
        '--path',
        type=Path,
        required=True,
        help='Path to target file',
    )
    args = parser.parse_args()

    main(args.path)
