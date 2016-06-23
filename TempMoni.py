# -*- coding: utf-8 -*-
"""
Author: xujm@realbio.cn
Ver2.0.1
Add critical alert also send sms
Ver:2.0.0
Add tts voice alert when the temperature above the critical level
Ver:1.0.0
init
"""

import os
import re
import subprocess
import json
import argparse
import logging
import top.api
import settings

parser = argparse.ArgumentParser(description="")
parser.add_argument('-s', '--smsphone', dest='smsphone', type=str, help='Send sms alert to this phone', required=True)
parser.add_argument('-t', '--ttsphone', dest='ttsphone', type=str, help='Send voice alert to this phone', required=True)
parser.add_argument('-v', '--verbose', action='store_true', dest='verbose', help='Enable debug info')
parser.add_argument('--version', action='version', version='2.0.1')


class NotifyTool:
    def __init__(self, sms_phone, tts_phone, host_name, dict_temp):
        self.sms_phone = sms_phone.strip()
        self.tts_phone = tts_phone.strip()
        self.host_name = host_name
        self.dict_temp = dict_temp
        self.appkey = settings.ALIDAYU_APPKEY
        self.secret = settings.ALIDAYU_SECRET

    def sms_temp_warn(self):
        logging.debug('sms config: {0} {1}, in_temp {2}'.format(self.appkey, self.secret, self.dict_temp['in_temp']))
        req = top.api.AlibabaAliqinFcSmsNumSendRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))
        # req.extend = "123456"
        req.sms_type = "normal"
        req.sms_free_sign_name = "锐翌集群"
        req.sms_param = json.dumps({'hostname': self.host_name, 'in_temp': str(self.dict_temp['in_temp']),
                                    'ex_temp': str(self.dict_temp['ex_temp'])})
        req.rec_num = self.sms_phone
        req.sms_template_code = "SMS_10845500"
        try:
            resp = req.getResponse()
            logging.debug('Sms send ok {0}'.format(resp))
            logging.info('Sms send ok')
            return 1
        except Exception as e:
            logging.info('Sms send error {0}'.format(e))
            return 0

    def tts_temp_crit(self):
        logging.debug('voice config: {0} {1}, in_temp {2}'.format(self.appkey, self.secret, self.dict_temp['in_temp']))
        req = top.api.AlibabaAliqinFcTtsNumSinglecallRequest()
        req.set_app_info(top.appinfo(self.appkey, self.secret))

        # req.extend="12345"
        req.tts_param = json.dumps({'hostname': self.host_name, 'in_temp': str(self.dict_temp['in_temp']),
                                    'ex_temp': str(self.dict_temp['ex_temp'])})
        req.called_num = self.tts_phone
        req.called_show_num = "051482043271"
        req.tts_code = "TTS_10970049"
        try:
            resp = req.getResponse()
            logging.debug('Tts voice send ok {0}'.format(resp))
            logging.info('Tts voice send ok')
            return 1
        except Exception as e:
            logging.info('Tts voice send error {0}'.format(e))
            return 0


class IpmiTool:
    def __init__(self, host_name):
        self.host_name = host_name

    def get_temp(self):
        handle = os.popen('/opt/rocks/bin/rocks run host {0} "ipmitool -c sdr type temperature"'.format(self.host_name))
        for i in handle:
            if re.search('^FP', i) or re.search('^Inlet', i):
                logging.debug('{1} inlet line {0}'.format(i, self.host_name))
                in_temp = int(i.split(',')[1])
            elif re.search('^MB', i) or re.search('^Exhaust', i):
                logging.debug('{1} exhaust line {0}'.format(i, self.host_name))
                ex_temp = int(i.split(',')[1])
        return {'in_temp': in_temp, 'ex_temp': ex_temp}


if __name__ == '__main__':
    args = parser.parse_args()
    smsphone = args.smsphone
    ttsphone = args.ttsphone
    hosts = ['nas-0-1', 'nas-0-2', 'nas-0-3', 'nas-0-4', 'nas-0-5', 'nas-0-6', 'nas-0-7', 'nas-0-8', 'nas-0-t',
             'data-0-1', 'data-0-2', 'data-0-3', 'data-0-4', 'data-0-6', 'data-0-7',
             'nas-1-1']
    ex_temp_warn = 50
    in_temp_warn = 30
    ex_temp_crit = 70
    in_temp_crit = 42
    sms_done_file = '/data_center_01/home/xujm/logs/sms.done'
    tts_done_file = '/data_center_01/home/xujm/logs/tts.done'

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="[%(asctime)s]%(name)s:%(levelname)s:%(message)s",
            filename='debug.log'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s]%(name)s:%(levelname)s:%(message)s",
            filename='/data_center_01/home/xujm/logs/TempMoniInfo.log'
        )

    for host in hosts:
        obj_ipmi = IpmiTool(host)
        d_temp = obj_ipmi.get_temp()
        obj_notify = NotifyTool(smsphone, ttsphone, host, d_temp)

        # Send tts voice and sms alert, when the temperature above critical level
        if d_temp['ex_temp'] >= ex_temp_crit or d_temp['in_temp'] >= in_temp_crit:
            if not os.path.exists(tts_done_file):
                recode_tts = obj_notify.tts_temp_crit()
                recode_sms = obj_notify.sms_temp_warn()
                if recode_tts:
                    subprocess.call(['touch', tts_done_file])
                    logging.debug('Touch tts.done ok: {0}'.format(recode_tts))
                    logging.info('Temp:{0} - {1} - {2}'.format(host, d_temp['in_temp'], d_temp['ex_temp']))
                    break
        else:
            if os.path.exists(tts_done_file):
                recode = subprocess.call(['rm', tts_done_file])
                logging.debug('Remove tts.done return code: {0}'.format(recode))

        # Send sms alert, when the temperature above warning level
        if d_temp['ex_temp'] >= ex_temp_warn or d_temp['in_temp'] >= in_temp_warn:
            if not os.path.exists(sms_done_file):
                recode = obj_notify.sms_temp_warn()
                if recode:
                    subprocess.call(['touch', sms_done_file])
                    logging.debug('Touch sms.done ok: {0}'.format(recode))
                    logging.info('Temp:{0} - {1} - {2}'.format(host, d_temp['in_temp'], d_temp['ex_temp']))
                    break
        else:
            if os.path.exists(sms_done_file):
                recode = subprocess.call(['rm', sms_done_file])
                logging.debug('Remove sms.done return code: {0}'.format(recode))
