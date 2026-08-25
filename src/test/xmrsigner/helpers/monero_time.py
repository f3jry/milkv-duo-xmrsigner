from __future__ import annotations
from unittest import TestCase

from xmrsigner.helpers.monero_time import MoneroTime, NetData, TestData, StageData
from typing import Union
from datetime import date, datetime, timedelta


NET_MAIN = 'main'
NET_TEST = 'test'
NET_STAGE = 'stage'


class TestMoneroTime(TestCase):

    def test_data(self):
        mainData = NetData.get_instance(NET_MAIN)
        testData = NetData.get_instance(NET_TEST)
        stageData = NetData.get_instance(NET_STAGE)

        self.assertEqual(mainData.birth, 1397818193)  # time of monero birth 2014-04-18 10:49:53 (1397818193)
        self.assertEqual(testData.birth, 1410295020)
        self.assertEqual(stageData.birth, 1518932025)

        self.assertEqual(mainData.v1_seconds_per_block, 60)  # avg seconds per block in v1
        self.assertEqual(testData.v1_seconds_per_block, 60)
        self.assertEqual(stageData.v1_seconds_per_block, 60)

        self.assertEqual(mainData.v2_time, 1458748658)  # time of v2 fork 2016-03-23 15:57:38 (1458748658)
        self.assertEqual(testData.v2_time, 1448285909)
        self.assertEqual(stageData.v2_time, 1520937818)

        self.assertEqual(mainData.v2_block, 1009827)
        self.assertEqual(testData.v2_block, 624634)
        self.assertEqual(stageData.v2_block, 32000)

        self.assertEqual(mainData.v2_seconds_per_block, 120)  # avg seconds per block in V2
        self.assertEqual(testData.v2_seconds_per_block, 120)
        self.assertEqual(stageData.v2_seconds_per_block, 120)

        self.assertEqual(mainData.rollback, 0)  # testnet got some huge rollbacks, so the estimation is way off
        self.assertEqual(testData.rollback, 342100)
        self.assertEqual(stageData.rollback, 30000)

    @staticmethod
    def network_to_js_network_name(net: str) -> str:
        return net.title() + 'net'

    @staticmethod  # code is intentionally left as much as possible untouched to have a valid reference
    def original_js_formula_for_appx_bc_height(_date: Union[int, date], _nettype: str, without_security_margin: bool = False):
        # time of monero birth 2014-04-18 10:49:53 (1397818193)
        moneroBirthTime = 1397818193 if _nettype == "Mainnet" else 1410295020 if  _nettype == "Testnet" else 1518932025
        #  avg seconds per block in v1
        secondsPerBlockV1 = 60
        # time of v2 fork 2016-03-23 15:57:38 (1458748658)
        forkTime = 1458748658 if  _nettype == "Mainnet" else 1448285909 if _nettype == "Testnet" else 1520937818
        # v2 fork block
        forkBlock = 1009827 if _nettype == "Mainnet" else 624634 if _nettype == "Testnet" else 32000
        # avg seconds per block in V2
        secondsPerBlockV2 = 120
        # time in UTC
        requestedTime = _date if type(_date) == int else int(datetime.fromisoformat(_date.isoformat()).timestamp())
        approxBlockchainHeight: int = None
        secondsPerBlock: int = None
        # before monero's birth
        if requestedTime < moneroBirthTime:
            return 0;
        # time between during v1
        if requestedTime > moneroBirthTime and requestedTime < forkTime:
            approxBlockchainHeight = int((requestedTime - moneroBirthTime) / secondsPerBlockV1)
            # console.log("Calculated blockchain height: " + approxBlockchainHeight );
            secondsPerBlock = secondsPerBlockV1;
        else:  # time is during V2
            approxBlockchainHeight =  int(forkBlock + (requestedTime - forkTime) / secondsPerBlockV2)
            # console.log("Calculated blockchain height: " + approxBlockchainHeight );
            secondsPerBlock = secondsPerBlockV2;

        if _nettype == "Testnet" or _nettype == "Stagenet":
            # testnet got some huge rollbacks, so the estimation is way off
            approximateTestnetRolledBackBlocks = 342100 if _nettype == "Testnet" else 30000
            if approxBlockchainHeight > approximateTestnetRolledBackBlocks:
                approxBlockchainHeight -= approximateTestnetRolledBackBlocks

        if without_security_margin:
            return max(approxBlockchainHeight, 0)

        blocksPerMonth = 60 * 60 * 24 * 30 / secondsPerBlock

        if approxBlockchainHeight - blocksPerMonth > 0:
            return approxBlockchainHeight - blocksPerMonth
        else:
            return 0

    def test_networks_against_legacy(self):
        for d in [date.fromisoformat(d) for d in [
            '2014-04-18',
            '2014-04-19',
            '2016-03-22',
            '2016-03-23',
            '2016-03-24',
            '2017-03-23',
            '2018-03-23',
            '2019-03-23',
            '2020-03-23',
            '2021-03-23',
            '2022-03-23',
            '2023-03-23',
            '2024-03-23',
            '2025-03-23',
            '2026-03-23',
            '2027-03-23',
            '2028-03-23',
            '2029-03-23',
            '2030-03-23'
            ]]:
            for network in (NET_MAIN, NET_TEST, NET_STAGE):
                # d: date = date.fromisoformat(d)
                ts: int = int(datetime.fromisoformat(d.isoformat()).timestamp())
                jsNetName: str = self.network_to_js_network_name(network)
                mt = MoneroTime(network, 0, True)
                self.assertEqual(mt.getBlockchainHeight(d), self.original_js_formula_for_appx_bc_height(d, jsNetName, True))
                self.assertEqual(mt.getBlockchainHeight(ts), self.original_js_formula_for_appx_bc_height(d, jsNetName, True))

    def test_height_to_date(self):
        mt = MoneroTime(NET_MAIN, 0, True)
        tt = MoneroTime(NET_TEST, 0, True)
        st = MoneroTime(NET_STAGE, 0, True)
        self.assertEqual(mt.getDate(0), date.fromisoformat('2014-04-18'))
        self.assertEqual(tt.getDate(0), date.fromtimestamp(1410295020))
        self.assertEqual(st.getDate(0), date.fromtimestamp(1518932025))
        self.assertEqual(mt.getDate(1009827), date.fromtimestamp(1458748658))
        self.assertEqual(tt.getDate(624634 + TestData.rollback), date.fromtimestamp(1448285909))  # we add the rollback blocks to check
        self.assertEqual(st.getDate(32000 + StageData.rollback), date.fromtimestamp(1520937818))  # we add the rollback blocks to check

if __name__ == '__main__':
    from unittest import main
    main()
