#!/usr/bin/env python3
"""Install shared AMS instructions and native OpenCode/Pi model presets."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
import os
import platform
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

if sys.version_info < (3, 11):
    raise SystemExit("OpenCode/Pi installation requires Python 3.11 or newer.")
import tomllib

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[1] if SCRIPT.name != "<stdin>" else Path.cwd()
REPOSITORY = "InsecurePassword/Codex-AMS"
REF = "main"
SKILL = "adaptive-master-subagent-orchestration"
MARKER = "<!-- managed-by: adaptive-master-subagent-orchestration -->"


# Exact native renders of frozen official d4819892cfd823b8b1d63c797edbb872279ee3da.
# Only the provider segment is normalized; all other bytes must match.
PRIOR_NATIVE_HASHES = {'opencode': {'ams_astra_high': '9edbfb9722a3e3e198c0409f8f02f9117c3134eb0fa4cb64f4929e38d08c0fcc',
              'ams_astra_low': 'f2b719706448127824561cef3297191128636f3254c455cb0494719b74f60a7a',
              'ams_astra_max': '3acc67701c704e37e0c5042f34e7afc5adcfa20c58a823f691889075ac21c534',
              'ams_astra_medium': '97e1caa10f6d5fbaefbd28d7e4b2dceb37ce37123d70b8c8977d31a24fe6b4f9',
              'ams_astra_xhigh': '8674ee9a8564058926e167c50f921571898aee5419092c0f1e5475dcff1ad43a',
              'ams_luna_high': '171dfcccf32bc7c5210985a26c75d877c8dbdfdd77dfd72021993b60cc8e7c46',
              'ams_luna_low': 'ea021af53a5941aeb023ae9abd84f830787430241c0b0249222ae90fb8019acd',
              'ams_luna_max': '6125951b278c1869fba367e1779eb143cd59e84968ba9795f3eef7ecbfe6e2f2',
              'ams_luna_medium': '27b77dc7c205e501d1ab29066487045473730b456a73500cc6b8f16ccb2c48b3',
              'ams_luna_xhigh': '93d959d2aa9a9c34b362d7cc87f2489136d568545f680b2672f85d9123480c7d',
              'ams_sol_high': 'cf23bbbd15c94c09c7724cf30d3cb2bea6837860ec283bece931891f7100a71d',
              'ams_sol_low': '1eca429b31be8d602977869f394cbae385ca081c14080292e746f13a6e7924e7',
              'ams_sol_max': '500a4badf50b82010cfac41204531d11f1ab5c35ae85412c7b84e58acaf44526',
              'ams_sol_medium': '24215051fd1b697cf73ace2804d67cb6db50cfe7a19c553c49bb393af747a8e2',
              'ams_sol_xhigh': 'f8343559fa8e9e1d122e4dacb7a352709e01906af6c678c515c34bca1ffab5db',
              'ams_spark_high': 'c216d22692173871ee36a53bf561118029d963848862e8f3ff846c4f3c65029a',
              'ams_spark_low': 'b0741648886399a87eff5cfc291c5d919e3a21159bf9a03b5c5e7c614b153437',
              'ams_spark_medium': '52eba50f07eff1ddb5f4b6de5a6737c7da1cd4adfa112a78f3910b5ee9e4be55',
              'ams_terra_high': '3b7b7d343922facc482b86e5aa1c2d66f7ea5d5fd0fb5f425b6b38129dba2b55',
              'ams_terra_low': 'ba575ec49cb0e439b61a912bca2a3d22e1a4baa72fae2282a80393468e71af02',
              'ams_terra_max': 'c5ce126d493e28c9f8bdffc4bbd94b9a45a91aef4f4c4b00c68877a21e9e67e7',
              'ams_terra_medium': '364ec0bf3774e280929a6a8858cbf3890094c4f990d8ca0d55b8ccdab1f45cc3',
              'ams_terra_xhigh': '0722173412fff075c8c26087844422d44b2635202063d3ba65e57edc5400bb24'},
 'pi': {'ams_astra_high': 'bd306fa168c95413dab110984ea81c057f58fe9905b551673372cd8fa9d1466b',
        'ams_astra_low': '54d875f2cfbe9be2dfd49919ccf2d06a15554dd3daaa8ae64176e2aaa6b2bdaf',
        'ams_astra_max': 'da4ce25ab797a3dd925d44f3956ccc41082140173c6a1bd5c2016473c38f15da',
        'ams_astra_medium': 'de9c115a187e6d9db37e16346eaa95d33916543cc184509c8c38f264744cd305',
        'ams_astra_xhigh': '77293397671d9817fb57aa583fb106ff95c2ed34a5fd0d58c85568f2c850babb',
        'ams_luna_high': '8ee9d4fa42a3a6cea40b66331328d98ab5424be713b3aba2cc2acb6fe972aafe',
        'ams_luna_low': '0015df6e8318232ba7328a93e35ac3c502d44f21f689492e17bf8be2f72b8aeb',
        'ams_luna_max': '671c35d1808975e1c463ac60363c902cf193e97ca88c500d9a407168a883e91c',
        'ams_luna_medium': 'f1fdaca294cf52fc8f65f330e0e703a2a9c632cf90678ffe5ee3e78ec3973f2c',
        'ams_luna_xhigh': '32d6dd3605e00f69e16c9686f2c28690b29a69eef582a1c0922f779ac8bcf455',
        'ams_sol_high': 'abfcc64ee78d646cca0b831ee95d29ddd283e2ae4f938bf2d76192f844f46984',
        'ams_sol_low': '1599f6dd4af1dc67f2e9434e2cdbe54dede2f68de4cff3d4561903161298ba64',
        'ams_sol_max': 'c5c2e95c2ad9900dfb498d15beba3d1cbc4bce556233d27e5a65d47d579026a6',
        'ams_sol_medium': '1ca8f2f617f80a0ff4d23be8ba721323303ba1e7ad7d4acd808e2144a6e17c43',
        'ams_sol_xhigh': '174cb541331bdf28655d96406717342f41cf97a0cc2f03fbf2b2c32d6aa9cd56',
        'ams_spark_high': '423c5b0d924996d7a8fc26fcff40da228b4dcf16fcaced060a2b648307387c56',
        'ams_spark_low': 'bbb06620a7080a394d4c8fc2cd0390ca2ac4a3bae60134f1dc0e6d11f9224cf4',
        'ams_spark_medium': 'ed3b86cff864594cea01fd6cff2c9524d7964484345d9453e1a003d109c7ef53',
        'ams_terra_high': '6a8c61ee6bca7ffa5673f7e575b440837c9417f460fc8261cd28a61186af785a',
        'ams_terra_low': '300ce909b2e8afd360d7a2a0506ab0808900dcbd880b65e799c5f6c88dad4e71',
        'ams_terra_max': '8cc2e32f0c8efce72b123123200db013dcc578de2fe1cc9589cc20ba47de6a38',
        'ams_terra_medium': '1c37e8e6aee876678833a801c9d33377b3feb6ee444e03bd80b9427b9cfaac0a',
        'ams_terra_xhigh': '8b21e9a30e8442af8f0c95e8dbfbee281f8ff3169d5599bc5518abf9ea9c9c0f'}}
# Exact stock renders of changed aliases from ac708b49b118c4c4a30b11b38df85bde6d0c5be5.
# Only the provider segment is normalized, as in the frozen table above.
MODEL_UPDATE_NATIVE_HASHES = {
    "opencode": {
        "ams_astra_high": "ed1de337e8fe74d5188b702ba34941c43ac791409dfe4da52a47c510635f4b40",
        "ams_astra_low": "7afc9e5083c16e538e445aacffd8875adb5bcadc7d4856d041f6308bbf774616",
        "ams_astra_max": "2286f6ed4a51ea54aba57ba71b6ebd85b98d39e6a30da5d8f71a64e96dc85e63",
        "ams_astra_medium": "b37c58eacaa01156dce6d726302d7b0469a11c53d6ff7da1b84e9c069e4c429e",
        "ams_astra_xhigh": "2713da4661d861a9114f512912508bff5d877a459f7ecb294200d26bc4e62999",
        "ams_sol_high": "fcd845d95ea79aca30915c19a9a9c2bb7f6146cb2af2d5db728dc0fbeef3fafc",
        "ams_sol_low": "de386788e75f793fd00709e94184c87db9e753b47ff9819623fb006076aa4132",
        "ams_sol_max": "8c6ed4011d6d10c6cdbc868cb800f38ba609947c7923a9461cb34e2bc4fff0ff",
        "ams_sol_medium": "d64983beb54b7031d3650a30ebb99116a5be3a02bc675206cc2dba63aa1912ad",
        "ams_sol_xhigh": "0d30fd28502494b2c64d56359735767ff445e6dbeaebf1da8cf827f48844309a",
        "ams_terra_high": "1eba887e33cd08f2da5a277e62d5d6387ec24c8937de676fa7fcc5983f414b42",
        "ams_terra_low": "ea416aa08d48597327679bd539904ee0ab4aa851c4f816a21d8637b1b31ff394",
        "ams_terra_max": "dd8254b0f468f72b1628d6296eca261624fa96a721712a5b62924b15912418a9",
        "ams_terra_medium": "a273c3673945ce87a61ec80fa35e72ee6c7d5637d8b1ba7299440f4a1bf1675f",
        "ams_terra_xhigh": "d34a2f7e45b57574258e251c916c194b20a9664b38feadd8675751ab1910cec9",
    },
    "pi": {
        "ams_astra_high": "0436df609a44c21a2be8fad805dadae31373cc404f0a84eb002d1b170242a37e",
        "ams_astra_low": "7c40444d4cb94c881becb296647c2b3bf1740682135bc8001d6799b2dd5845dd",
        "ams_astra_max": "a1f059732084d60b1136f220592b1f86e1a3b308c30c590b091f60cc2d643391",
        "ams_astra_medium": "42fac30eda95b01adcea1160e59aee3ce73dfd18d4535d2c553095b08c487719",
        "ams_astra_xhigh": "31ba8844edd83a0926e5ee097df384b6355415a1dad6d299700e5540060103f9",
        "ams_sol_high": "ef6e16a46b3dfc35d8385a59934b3a588bbb6f5e0cb2850c1074d04ca8cd9ddc",
        "ams_sol_low": "89b2b997fe9712bd2189fdc0143fe8bd29e5e1a091c26b4a26301b57d9910be5",
        "ams_sol_max": "116acf04f1d573ddbd804286cf6538481fddddf8b667d0c1cd88be2842fea088",
        "ams_sol_medium": "1366441b78612be298146b4fb9127218c2ab3565e8d79c0ae6b2b6b72950c533",
        "ams_sol_xhigh": "4c782ff3801c16ecc07968a96e2f178b4abc4d7c9a6a3dc366be32c688721dc6",
        "ams_terra_high": "dea8472fd09e0c3807f5b6c3a6024de5eb7226e8a9820f7b4e22c14ca07a3479",
        "ams_terra_low": "5b6cb3d6202747991dd15cdb286ad8716feb7f8db52552c6bc2c654913c00cb8",
        "ams_terra_max": "7b0de99eec0ae22f8f1903ee6343ec227bf8100067f39fe0d1daddc916a24c2e",
        "ams_terra_medium": "f7a2d6c0b22219925cf0de577135bf2474ca8687a34709c5f0dac7b22192c3bb",
        "ams_terra_xhigh": "ccc7e823dcad1051c23ea1761bd2e5747301a949b886bab6d59f09b5c13048d7",
    },
}
# Exact stock renders (current predecessors and retired aliases) from f2462569cf9223a14d438ea4a0bdd490e9dd3d0a.
EFFORT_UPDATE_NATIVE_HASHES = {
    "opencode": {
        "ams_sol_6_0_low": "5b220ea2dfa022f50620bd6814cdc67c084911d4a47473935e08710901600cc3",
        "ams_sol_6_0_medium": "2c0d2504d52e9417212eb6cfc872c2428cb52da980705369c21b1dc90f45adec",
        "ams_sol_6_0_high": "f9d6fc5c64860e8ac86d6cd2c5a973607cdfd24d7e3e30513faec810d719713e",
        "ams_sol_6_0_xhigh": "6c24b7a4743344fdf76b76e28baf02ad49047d59be1a41c6aa38c4c97aa85750",
        "ams_sol_6_0_max": "d23d1481484caa7bcbd094b96d098cae7d32012b641777488093d031c341cbf1",
        "ams_sol_5_6_low": "4e86464dd0b3f87ff8d2f9222e5fe0a83ee3f4ba7a561d59c09d066cd88c67f8",
        "ams_sol_5_6_medium": "a6805e32f1db24977a7096730ed5a37217c168879882fceffe70ae666fee66fc",
        "ams_sol_5_6_high": "a2436633e5eda7c951387032709944d502609f5a99a5ee145c90c8028a606726",
        "ams_sol_5_6_xhigh": "2de493cbe06c308736ceadc596562dfd6bab98b0b7b5f2f81440291124adddde",
        "ams_sol_5_6_max": "b050572fb3909c3f72f62436bb57f26ae17308d9290cd88aaa9ab5c348b6234b",
        "ams_luna_5_6_low": "f29106974484ff3450284c747463951ee1117aaa12021dda073545d9e3a75dcd",
        "ams_luna_5_6_medium": "d2237ac29c7e27ff814e2bea56ac2485b2eea84420625ce1c3610738626ae87e",
        "ams_luna_5_6_high": "44a55386d5e782f7e7aa680b98da4b0922ac9088d74f768a2d8db58456389be7",
        "ams_luna_5_6_xhigh": "d1a57dbf665811b3b7d244a63b78488414fd21fa5d4a5bc51e9e6c9d728b3b95",
        "ams_luna_5_6_max": "a1c207cdef39467e1a6966679a01c5a1b01f5cc13d748f6f692e5c17ba0524cc",
        "ams_astra_high": "45143850e40ea7bb5a0777e743f18ca0203ff8ab42d5d0f8d9feb104557934e2",
        "ams_astra_low": "518b3805fe5765070ad534b50b0fa5e99f1dbf0101955a1b67b3326858f566e6",
        "ams_astra_max": "897a048ab681a92edca3f6ec4a1e30b7985b95765bbf306e1383f8d98f1820e6",
        "ams_astra_medium": "0c2c4f3d29cc07d408d9532ec4e4e67816c4f4f48c5449cd11afba4a113cefa5",
        "ams_astra_xhigh": "59a2e983a38518e366883000a0b17880ba2ec17d589a62a713eb5e2798c84af6",
        "ams_luna_high": "949e3c14896054731af5e4f8476bf703ed67ba223770deed31b5dc20e653e130",
        "ams_luna_low": "257139dfbbbd1c0d0a93d1d90651fe1bf11653769bc62f6296e1cf39b4fb25a8",
        "ams_luna_max": "11f9be083ebafb15b329b790b5943a09bbc70bc748c4d14f3ad6e719e390b3ad",
        "ams_luna_medium": "4500dbae462f9870eaac6d871a270376e3db83b9542b84ff2f97c7b0e5dbab80",
        "ams_luna_xhigh": "7b16d082f1e90ec3f11f32e4292bf1679aa44df911c5fc04310c4620601fdc15",
        "ams_sol_high": "b182e4b486ba872fe9fe4b993a074f24d1af38feb264cc957dbe110c82224d48",
        "ams_sol_low": "4bb6b5f8022d6f47d8a53d3aaf25c063835d720b05acf8662d78712b5ae9bfc9",
        "ams_sol_max": "d70946f24fb75a1cae099af8918355996a11a59f4fe3de957da5142528afaf0f",
        "ams_sol_medium": "f043e95567079d6a85a3d12ac3e31489df0c45ff2393c40431c36871bf2b0423",
        "ams_sol_xhigh": "29b05633ac4dbfa7d5f95b48dfe4cbfea500f3d5ee5b18f88f8b07c254500db0",
        "ams_terra_high": "736a7312b154365c189bfd37221ff7757298bb5fd60d89f2019577cb58fb49f8",
        "ams_terra_low": "b0ee44150e372d44e29d50c60016167d548875719561ef1f3f2b236662fe6176",
        "ams_terra_max": "21d52d2a27c0297026403d53a8fee1b5d2d2b5448ee099ee91588d732013d84a",
        "ams_terra_medium": "8c44ccbc74b2667a78c8931c533945002c70220847dc03cb4980933f0e03bab0",
        "ams_terra_xhigh": "c38ac31cb3853056636b018e5c343348c21299181e1e394718d791be656bf55b",
    },
    "pi": {
        "ams_sol_6_0_low": "eaaa5d05967c6c87169e240af35217ea15ef8a1ae78ce6eff718cba2da5ef30b",
        "ams_sol_6_0_medium": "91a42439b4132695b9f0cc8e4ff3b2f6bab89fd7381048c5722cfe136a197c6d",
        "ams_sol_6_0_high": "36c94aefcfe1b8c8348ab78a5994e98ddd9248a40dd293fb6541d111d84bcdfa",
        "ams_sol_6_0_xhigh": "88fd485078dd59441bc21a9fdda68abab1c934b7e9b9146e8a7816e9ae8af7e4",
        "ams_sol_6_0_max": "a3527fd7c5c93501066b8e0ac5f41ef463420bc32cedb336e225188ed25b556a",
        "ams_sol_5_6_low": "3a16110a59754b1b1e03fe747d5e480b83168d10a6d94b738e2f71118944c2b7",
        "ams_sol_5_6_medium": "b82bb75cbe7b2ccde59c31744f018d1da1887b03a5116da60cb7b4447d256c5a",
        "ams_sol_5_6_high": "8d91ca9559500a27e9a3b5178a84a11f14b65ac8fe6126f870796036c3ca0b3a",
        "ams_sol_5_6_xhigh": "34b3697920b8f7a20316bbe96cb0e5b9758afe41c96c0213857cd0f7af5c0f93",
        "ams_sol_5_6_max": "817e17bd66af55b49e6f430e76631b12084754e37b9ae7005cec7b4ac0e7de0e",
        "ams_luna_5_6_low": "3a2a35880c3a61686c7a4b3c6a365f06ca026cdeeae3be57ff2b84b0e175a635",
        "ams_luna_5_6_medium": "9286108ac4d5ac5316b092f0b712dbd4a2409b7ae1fd0a8bada153218acf9bca",
        "ams_luna_5_6_high": "09902c620cd6318829825d79c8907c4722f378c2655b205b1c31788dae055040",
        "ams_luna_5_6_xhigh": "f8125f7f8f542e4817c3e98179e1ec0593ed6813936437db82f421925e2d06b9",
        "ams_luna_5_6_max": "af85c64d548ab1a9702268b12bf102b2c80745c17715a6258e59242a0f334977",
        "ams_astra_high": "626ef5d157382e36e40f1ce80de7db6e896231f6e11c3db1fe44597e45b2a7cb",
        "ams_astra_low": "bace3849bf38e7c3135a41a092f3f71dc57361ffe033cf61c4dd710267bf7184",
        "ams_astra_max": "9b734d459124ee82ec5f35899c4e24156c6a075d413929bbc0658365a12648e2",
        "ams_astra_medium": "53dd2e056a6e87ce43e425869c4a0b2f4e727ce7626ba0bd58018401bb04a250",
        "ams_astra_xhigh": "5d522689241a70852ff12090babd1de166fec45577f34208b587b0998b46274b",
        "ams_luna_high": "99a9ebe71eb27ea5aff7b3fef0c46cfacaf64613127865c4f8dac5b1b5b60a9a",
        "ams_luna_low": "8807883f14aa260f9747cf6a96267e3fe942578fff7e708fdde6c0d37fab4e1c",
        "ams_luna_max": "78db2395ca70388bebe0274fdb037ba0f5de01a96014370079429a4ce903a05b",
        "ams_luna_medium": "95f3bdd8eea60502bf0759b8f2c28476e98afafae7d42e3c0c1c33c7cb967ae0",
        "ams_luna_xhigh": "1b3d8e50b069ea60cfc1954e34e6ccd299bccd7fecd1138444068c7811b68e47",
        "ams_sol_high": "53f48abb67e5288b7131c72ae516efa71ed73be61aedde353290761aed6e0a7f",
        "ams_sol_low": "d1b997c9ea87185cd0bdb1293321512963629c431b23858b4b51495823129638",
        "ams_sol_max": "d8baa1b78c1070868d472f4b6c9641e819a25a100dfc3eda3ee3d7dad19169f5",
        "ams_sol_medium": "1c17598487327d13a82847d6a9b4fa3e06e8960d74de64f23da0b7d54d8fad54",
        "ams_sol_xhigh": "7694732dc186e1211ea74faa67414ff136eae69b39a08a9f3800f9303c8691a4",
        "ams_terra_high": "b1d60c9cbbfaea5e92806c539f96f46679d9d163d2beef09f9795d502b2482ef",
        "ams_terra_low": "7f109b5a0069f2571b90ac96f6fa88951cb0bb0ecba49a8e2f8c5f42f7bf1cb2",
        "ams_terra_max": "4ae83c792db111a5d88334580db57981785fc95ed55ac3284859d13531b826f9",
        "ams_terra_medium": "e73e60c00bf776ec1997549d2dc89e386bfead2feca6524c6a4f9f7c6919406d",
        "ams_terra_xhigh": "f1c3ce661e275707b6994954b12b5aee58ac19c77d1c9ad5ca13fe1bf178a506",
    },
}
RETIRED_NATIVE_NAMES = ("ams_spark_low", "ams_spark_medium", "ams_spark_high") + tuple(
    f"ams_{family}_{effort}" for family in ("sol_6_0", "sol_5_6", "luna_5_6")
    for effort in ("low", "medium", "high", "xhigh", "max")
)
EXPECTED_PROFILE_NAMES = {
    f"ams_{family}_{effort}" for family in
    ("sol", "luna", "astra", "terra")
    for effort in ("low", "medium", "high", "xhigh", "max")
} | {"ams_daybreak_blue_max"}


def safe_path(path: Path) -> None:
    """Reject redirected targets without changing any filesystem permissions."""
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Redirected installation path: {part}")
        if part != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"Installation parent is not a directory: {part}")


def anchored_home(value: str | Path) -> Path:
    """Pin selected-root ancestor aliases without accepting a redirected root leaf."""
    path = Path(value).expanduser().absolute()
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError(f"Redirected installation root: {path}")
    return path.resolve()


def home_path(variable: str, default: Path) -> Path:
    return anchored_home(os.environ.get(variable) or default)


@lru_cache(maxsize=1)
def github_token() -> str | None:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token.strip()
    gh = shutil.which("gh")
    if gh:
        result = subprocess.run([gh, "auth", "token"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    return None


def _remote_bytes(path: str) -> bytes:
    quoted = "/".join(urllib.parse.quote(part, safe="") for part in path.split("/"))
    # Public installs use raw downloads, not one rate-limited API request per file.
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{REF}/{quoted}"
    headers = {"User-Agent": "AMS-Tree-Installer"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(1048577)
    except urllib.error.HTTPError as error:
        token = github_token() if error.code in (401, 403, 404) else None
        if not token:
            raise ValueError(f"Repository download failed (HTTP {error.code}): {path}. "
                             "Check connectivity and repository access; no files were substituted.") from error
        url = f"https://api.github.com/repos/{REPOSITORY}/contents/{quoted}?ref={REF}"
        headers.update(Accept="application/vnd.github.raw+json", Authorization=f"Bearer {token}")
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
            data = response.read(1048577)
    if len(data) > 1048576:
        raise ValueError(f"Repository file exceeds the installation size limit: {path}")
    return data


@lru_cache(maxsize=None)
def remote_bytes(path: str) -> bytes:
    return _remote_bytes(path)


def source_bytes(path: str, local: bool) -> bytes:
    if local:
        source = ROOT / path
        safe_path(source)
        return source.read_bytes()
    return remote_bytes(path)


def manifest_entries(data: bytes) -> dict[str, tuple[str, int]]:
    if (not data.startswith(b"ams-install-manifest-v1\n") or not data.endswith(b"\n")
            or b"\r" in data or len(data) > 262144):
        raise ValueError("Invalid installation manifest.")
    entries: dict[str, tuple[str, int]] = {}
    folded: set[str] = set()
    for row in data.decode("utf-8").splitlines()[1:]:
        digest, length_text, name = row.split("\t")
        parts = name.split("/")
        if (parts[0] != SKILL or any(part in ("", ".", "..") for part in parts)
                or not re.fullmatch(r"[A-Za-z0-9._/-]+", name) or name.casefold() in folded
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not length_text.isdecimal() or not 0 < int(length_text) <= 1048576):
            raise ValueError(f"Unsafe or duplicate manifest entry: {name}")
        entries[name] = (digest, int(length_text))
        folded.add(name.casefold())
    if not entries or sum(size for _, size in entries.values()) > 104857600:
        raise ValueError("Installation manifest has invalid membership or total size.")
    return entries


def package_profiles(local: bool = True) -> list[dict[str, str]]:
    entries = manifest_entries(source_bytes("install-manifest.txt", local))
    names = sorted(name for name in entries if "/assets/agent-profiles/" in name and name.endswith(".toml"))
    if {Path(name).stem for name in names} != EXPECTED_PROFILE_NAMES or len(names) != 21:
        raise ValueError("Expected the exact 21 manifest-listed AMS model profiles.")
    profiles = []
    for name in names:
        data = source_bytes(name, local)
        digest, length = entries[name]
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Package integrity check failed: {name}")
        profile = tomllib.loads(data.decode("utf-8"))
        if profile["name"] != Path(name).stem:
            raise ValueError(f"Profile name mismatch: {name}")
        if profile["name"] != "ams_daybreak_blue_max":
            profiles.append(profile)
    return profiles


def windows_gui(path: Path) -> bool:
    """Inspect the PE subsystem without launching a Windows desktop application."""
    if path.suffix.lower() != ".exe":
        return False
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            return False
        stream.seek(int.from_bytes(header[60:64], "little"))
        pe = stream.read(94)
    return (len(pe) == 94 and pe[:4] == b"PE\0\0"
            and int.from_bytes(pe[92:94], "little") == 2)


def running_opencode_desktops(env: dict[str, str]) -> dict[int, str]:
    """Inspect this Windows session's Desktop processes; never stop them or read credentials."""
    if os.name != "nt":
        return {}
    powershell = shutil.which("powershell.exe")
    if not powershell:
        raise ValueError("Windows PowerShell is required to check whether OpenCode Desktop is still running.")
    script = r"""$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$session = [Diagnostics.Process]::GetCurrentProcess().SessionId
$items = @(Get-Process | Where-Object {
    $_.SessionId -eq $session -and $_.ProcessName -match '^opencode(?:[ -](?:desktop|beta|dev))?$'
} | ForEach-Object { @{ id = $_.Id; path = $_.Path } })
ConvertTo-Json -InputObject $items -Compress
"""
    check_env = env.copy()
    check_env.pop("PSModulePath", None)
    result = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", script],
                            env=check_env, stdin=subprocess.DEVNULL, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=20)
    if result.returncode:
        raise RuntimeError("Could not inspect OpenCode Desktop processes. No process was stopped.")
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValueError("Invalid OpenCode Desktop process-check response.") from error
    if not isinstance(rows, list):
        raise ValueError("Invalid OpenCode Desktop process-check response.")
    active: dict[int, str] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("id"), int) or row["id"] <= 0:
            raise ValueError("Invalid OpenCode Desktop process identity.")
        location = row.get("path")
        if not location:
            active[row["id"]] = "OpenCode (executable path unavailable)"
            continue
        if not isinstance(location, str):
            raise ValueError("Invalid OpenCode Desktop process path.")
        try:
            if windows_gui(Path(location)):
                active[row["id"]] = location
        except FileNotFoundError:
            continue  # The process exited during inspection.
    return active


def wait_for_opencode_desktop_exit(env: dict[str, str], timeout: float = 120) -> None:
    """Prevent a successful file install from leaving an already-open Desktop on its old agent cache."""
    active = running_opencode_desktops(env)
    if not active:
        return
    print("opencode: WAITING FOR DESKTOP TO CLOSE. Finish or pause your work, then quit OpenCode Desktop normally.", flush=True)
    print("The installer will continue automatically after Desktop exits (up to 120 seconds). Keep it closed until installation finishes.", flush=True)
    print("No AMS files have been changed. The installer will not close apps or terminate your agents.", flush=True)
    print("OpenCode Desktop process IDs: " + ", ".join(map(str, sorted(active))), flush=True)
    deadline = time.monotonic() + timeout
    while active:
        if time.monotonic() >= deadline:
            raise RuntimeError("OpenCode Desktop is still running. No AMS files were changed. Quit Desktop normally, then run the installer again.")
        time.sleep(1)
        active = running_opencode_desktops(env)
    print("opencode: Desktop has exited. Continuing installation.", flush=True)


def desktop_version(executable: Path) -> str | None:
    """Read Electron's package metadata without executing or editing the desktop app."""
    archive = executable.parent / "resources/app.asar"
    if not archive.is_file():
        return None
    safe_path(archive)
    with archive.open("rb") as stream:
        prefix = stream.read(8)
        if len(prefix) != 8:
            raise ValueError(f"Invalid desktop package: {archive}")
        marker, length = struct.unpack("<II", prefix)
        if marker != 4 or not 8 <= length <= 16 * 1024 * 1024:
            raise ValueError(f"Invalid desktop package header: {archive}")
        header = stream.read(length)
        if len(header) != length:
            raise ValueError(f"Truncated desktop package: {archive}")
        size = struct.unpack_from("<I", header, 4)[0]
        if size > length - 8:
            raise ValueError(f"Invalid desktop package index: {archive}")
        entry = json.loads(header[8:8 + size]).get("files", {}).get("package.json", {})
        offset, size = str(entry.get("offset", "")), entry.get("size", 0)
        if not offset.isdecimal() or not isinstance(size, int) or not 0 < size <= 65536:
            raise ValueError(f"Missing desktop package metadata: {archive}")
        stream.seek(8 + length + int(offset))
        package = json.loads(stream.read(size))
    version = package.get("version", "")
    if package.get("name") != "@opencode-ai/desktop" or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Not a supported stable OpenCode Desktop package: {archive}")
    return version


def download_desktop_cli(version: str, directory: Path) -> str:
    """Stage a checksum-verified official CLI matching Windows Desktop; never install it globally."""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid OpenCode Desktop version.")
    arch = {"amd64": "x64-baseline", "x86_64": "x64-baseline", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine().lower())
    if not arch:
        raise ValueError("Unsupported Windows architecture for temporary OpenCode CLI.")
    name = f"opencode-windows-{arch}.zip"
    base = "https://github.com/anomalyco/opencode/releases/download/v" + version
    request = urllib.request.Request(
        f"https://api.github.com/repos/anomalyco/opencode/releases/tags/v{version}",
        headers={"User-Agent": "AMS-Tree-Installer"})
    with urllib.request.urlopen(request, timeout=60) as response:
        metadata = response.read(1048577)
    if len(metadata) > 1048576:
        raise ValueError("OpenCode release metadata exceeds the size limit.")
    release = json.loads(metadata)
    matches = [a for a in release.get("assets", []) if a.get("name") == name]
    if release.get("tag_name") != "v" + version or release.get("draft") or release.get("prerelease") or len(matches) != 1:
        raise ValueError(f"No exact official OpenCode {version} CLI asset: {name}")
    asset = matches[0]
    digest, size = asset.get("digest", ""), asset.get("size", 0)
    if (not re.fullmatch(r"sha256:[0-9a-f]{64}", digest) or not isinstance(size, int)
            or not 0 < size <= 256 * 1024 * 1024 or asset.get("browser_download_url") != base + "/" + name):
        raise ValueError("OpenCode CLI release asset has invalid URL, size, or checksum metadata.")
    archive = directory / name
    checksum, total = hashlib.sha256(), 0
    print(f"opencode: downloading temporary official CLI {version} ({size // 1048576} MiB).", flush=True)
    with urllib.request.urlopen(urllib.request.Request(base + "/" + name, headers={"User-Agent": "AMS-Tree-Installer"}), timeout=60) as response, archive.open("xb") as output:
        while chunk := response.read(1048576):
            total += len(chunk)
            if total > size:
                raise ValueError("OpenCode CLI download exceeds its declared size.")
            checksum.update(chunk)
            output.write(chunk)
    if total != size or checksum.hexdigest() != digest[7:]:
        raise ValueError("OpenCode CLI download failed its size/SHA-256 check.")
    executable = directory / "opencode.exe"
    try:
        with zipfile.ZipFile(archive) as bundle:
            binaries = [i for i in bundle.infolist() if i.filename.split("/")[-1] == "opencode.exe"]
            if len(binaries) != 1:
                raise ValueError("OpenCode CLI archive must contain exactly one executable.")
            entry = binaries[0]
            if (".." in entry.filename.split("/") or "\\" in entry.filename
                    or stat.S_ISLNK(entry.external_attr >> 16) or not 0 < entry.file_size <= 512 * 1024 * 1024):
                raise ValueError("Invalid OpenCode CLI archive member.")
            with bundle.open(entry) as source, executable.open("xb") as output:
                shutil.copyfileobj(source, output)
            if executable.stat().st_size != entry.file_size:
                raise ValueError("OpenCode CLI extraction size mismatch.")
    except zipfile.BadZipFile as error:
        raise ValueError("Invalid OpenCode CLI archive.") from error
    return str(executable)


def opencode_cli(env: dict[str, str], download_dir: Path | None = None) -> str:
    """Find a working CLI, preferring the desktop's own sidecar over its GUI."""
    override = env.get("AMS_OPENCODE_CLI")
    if override:
        selected = Path(override).expanduser()
        if not selected.is_absolute():
            raise ValueError("AMS_OPENCODE_CLI must be the full path to a CLI executable.")
        candidates = [selected]
    else:
        directories = [Path(p.strip('"')) for p in env.get("PATH", "").split(os.pathsep) if p]
        if os.name == "nt" and env.get("LOCALAPPDATA"):
            local = Path(env["LOCALAPPDATA"])
            directories += [local / "Programs/@opencode-aidesktop", local / "Programs/OpenCode", local / "OpenCode"]
        candidates = []
        for directory in directories:
            # Electron uses resources/; older Tauri packages use a sibling sidecar.
            candidates += [directory / "resources/opencode-cli.exe", directory / "opencode-cli.exe"]
            for name in ("opencode", "opencode.exe", "opencode.cmd", "opencode.bat", "opencode-cli"):
                candidates.append(directory / name)
    checked: list[str] = []
    desktops: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(os.path.abspath(candidate))
        if key in seen:
            continue
        seen.add(key)
        if not candidate.is_file():
            continue
        try:
            if windows_gui(candidate):
                checked.append(f"{candidate}: desktop launcher, not run")
                if not override and download_dir is not None and os.name == "nt":
                    version = desktop_version(candidate)
                    if version:
                        desktops.append((candidate, version))
                continue
            result = subprocess.run([str(candidate.absolute()), "--version"], cwd=Path.cwd(), env=env,
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=15)
            version = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout).strip()
            if result.returncode == 0 and re.fullmatch(
                    r"(?:opencode(?:-cli)?\s+)?v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", version, re.IGNORECASE):
                return str(candidate.absolute())
            checked.append(f"{candidate}: no valid CLI version (exit {result.returncode})")
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            checked.append(f"{candidate}: {error}")
    if desktops and download_dir is not None:
        desktop, version = desktops[0]
        print(f"opencode: Desktop {version} at {desktop} has no usable installed CLI.", flush=True)
        executable = download_desktop_cli(version, download_dir)
        result = subprocess.run([executable, "--version"], cwd=Path.cwd(), env=env,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=30)
        if result.returncode or result.stdout.strip().removeprefix("v") != version:
            raise ValueError("Downloaded OpenCode CLI does not report the exact Desktop version.")
        return executable
    detail = "; ".join(checked) or "No CLI executable found in the selected locations."
    raise ValueError("No working OpenCode CLI found. " + detail +
                     " Use the desktop's opencode-cli.exe or an installed OpenCode CLI; "
                     "set AMS_OPENCODE_CLI to its full path for a custom location. "
                     "No provider or model availability was inferred.")


def cli(harness: str, arguments: list[str], *, env: dict[str, str]) -> str:
    executable = (env.get("AMS_OPENCODE_CLI") or opencode_cli(env)
                  if harness == "opencode" else shutil.which(harness))
    if not executable:
        raise ValueError(f"{harness} is not on PATH. Install the harness first.")
    result = subprocess.run([executable, *arguments], cwd=Path.cwd(), env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode:
        raise RuntimeError(f"{harness} {' '.join(arguments)} failed (exit {result.returncode}); no model was invoked.")
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    if harness == "opencode" and not output.strip():
        raise ValueError(f"OpenCode CLI returned no output for {' '.join(arguments)}: {executable}. "
                         "This is not evidence that your account lacks AMS models.")
    return output


def verify_opencode_agents(files: dict[Path, bytes], env: dict[str, str]) -> None:
    output = cli("opencode", ["agent", "list"], env=env)
    names = set(re.findall(r"^([^\s]+) \((?:subagent|all)\)\s*$", output, re.MULTILINE))
    missing = {path.stem for path in files} - names
    if missing:
        raise ValueError("OpenCode did not register the installed agents: " + ", ".join(sorted(missing)) +
                         ". Check the active config directory and disabled/project agent overrides.")


def catalog(harness: str, env: dict[str, str]) -> dict[str, set[str]]:
    output = cli(harness, ["models"] if harness == "opencode" else ["--list-models"], env=env)
    models: dict[str, set[str]] = {}
    for line in output.splitlines():
        fields = line.split()
        if harness == "opencode" and len(fields) == 1 and "/" in fields[0]:
            provider, model = fields[0].split("/", 1)
        elif harness == "pi" and len(fields) >= 2 and fields[0].lower() != "provider":
            provider, model = fields[:2]
        else:
            continue
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", provider) and model:
            models.setdefault(model, set()).add(provider)
    return models


def select_profiles(profiles: list[dict[str, str]], models: dict[str, set[str]],
                    harness: str, provider: str, agent_home: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for profile in profiles:
        candidates = models.get(profile["model"], set())
        if provider != "auto":
            candidates = candidates & {provider}
        target = agent_home / (profile["name"] + ".md")
        safe_path(target)
        if not candidates:
            if target.is_file() and predecessor_provider(profile["name"], target.read_bytes(), harness) is not None:
                raise ValueError(f"Installed predecessor {profile['name']} needs exact model {profile['model']}, "
                                 "which is not listed by the selected provider. Existing files were preserved.")
            continue
        # Auto preserves an exact generated route, including an official prompt/model
        # predecessor. A marker or a plausible frontmatter field is never ownership proof.
        prior = target.read_bytes() if target.is_file() else None
        previous = [p for p in candidates if prior == render(profile, harness, p)]
        old_provider = predecessor_provider(profile["name"], prior, harness) if prior is not None else None
        if provider == "auto" and old_provider is not None:
            if old_provider not in candidates:
                raise ValueError(f"Previous provider {old_provider!r} does not list {profile['model']}. "
                                 f"Select --{harness}-provider NAME explicitly to change this route.")
            candidates = {old_provider}
        elif len(candidates) > 1:
            if len(previous) != 1:
                raise ValueError(f"{profile['model']} is listed by multiple providers: "
                                 f"{', '.join(sorted(candidates))}. Select --{harness}-provider NAME.")
            candidates = set(previous)
        files[target] = render(profile, harness, next(iter(candidates)))
    if not files:
        providers = sorted({p for available in models.values() for p in available})
        examples = ", ".join(sorted(models)[:8]) or "(empty model catalog)"
        raise ValueError("No exact AMS model IDs found" +
                         (f" under provider {provider!r}" if provider != "auto" else " in any provider") +
                         f". Listed providers: {', '.join(providers) or '(none)'}. "
                         f"Model examples: {examples}. No model names were substituted.")
    return files


def pi_package(pi_home: Path) -> bool:
    settings = pi_home / "settings.json"
    if not settings.exists():
        return False
    data = json.loads(settings.read_text(encoding="utf-8-sig"))
    for item in data.get("packages", []):
        source = item.get("source", "") if isinstance(item, dict) else item
        if isinstance(source, str) and (re.fullmatch(r"npm:pi-subagents(?:@[^\s]+)?", source)
                                       or source.startswith("git:github.com/nicobailon/pi-subagents")):
            if isinstance(item, dict) and item.get("extensions") == []:
                raise ValueError("pi-subagents extensions are disabled; enable them with pi config before installing AMS.")
            return True
    return False


def render(profile: dict[str, str], harness: str, provider: str) -> bytes:
    fields = {
        "description": profile["description"],
        "model": f"{provider}/{profile['model']}",
    }
    if harness == "opencode":
        fields.update(mode="subagent", reasoningEffort=profile["model_reasoning_effort"])
    else:
        fields.update(name=profile["name"], thinking=profile["model_reasoning_effort"], systemPromptMode="append")
    # JSON-quoted strings are valid YAML; no YAML dependency or provider settings edits.
    frontmatter = "\n".join(f"{key}: {json.dumps(value)}" for key, value in fields.items())
    return (f"---\n{frontmatter}\n---\n{MARKER}\n\n{profile['developer_instructions'].strip()}\n").encode("utf-8")


def predecessor_provider(name: str, data: bytes, harness: str) -> str | None:
    expected = (PRIOR_NATIVE_HASHES[harness].get(name), MODEL_UPDATE_NATIVE_HASHES[harness].get(name),
                EFFORT_UPDATE_NATIVE_HASHES[harness].get(name))
    if not any(expected):
        return None
    match = re.search(rb'^model: "([A-Za-z0-9][A-Za-z0-9._-]*)/([^"\r\n]+)"$', data, re.MULTILINE)
    if not match:
        return None
    normalized = data[:match.start(1)] + b"ams-predecessor" + data[match.end(1):]
    if hashlib.sha256(normalized).hexdigest() not in expected:
        return None
    return match.group(1).decode("ascii")


@contextmanager
def native_lock(home: Path):
    """Serialize native writers; an existing lock fails closed without stale guesses."""
    safe_path(home)
    home.mkdir(parents=True, exist_ok=True)
    path = home / ".adaptive-master-subagent-orchestration.native.lock"
    safe_path(path)
    try:
        path.mkdir()
    except FileExistsError as error:
        raise ValueError(f"Another native AMS transaction may be active: {path}") from error
    identity = path.stat()
    try:
        yield
    finally:
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == (identity.st_dev, identity.st_ino):
            path.rmdir()


def regular_snapshot(path: Path) -> tuple[tuple[int, int], bytes]:
    safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Agent target is not regular: {path}")
    data = path.read_bytes()
    after = path.lstat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError(f"Agent changed during inspection: {path}")
    return (after.st_dev, after.st_ino), data


def preflight(files: dict[Path, bytes]) -> dict[Path, tuple[tuple[int, int], bytes]]:
    previous = {}
    for path, data in files.items():
        safe_path(path)
        if path.exists():
            identity, prior = regular_snapshot(path)
            harness = "pi" if b'\nsystemPromptMode: "append"\n' in data else "opencode"
            if prior != data:
                if predecessor_provider(path.stem, prior, harness) is None:
                    raise ValueError(f"Preserving differing agent file: {path}. Reconcile it before reinstalling.")
                previous[path] = (identity, prior)
    return previous


# Replacement journal: target, published identity/data (None for removal),
# actual displaced entry, expected predecessor snapshot.
Replacement = tuple[Path, tuple[int, int] | None, bytes | None, Path, tuple[tuple[int, int], bytes]]


def create_files(files: dict[Path, bytes], created: list[tuple[Path, tuple[int, int], bytes]],
                 replaced: list[Replacement], backups: Path,
                 previous: dict[Path, tuple[tuple[int, int], bytes]]) -> None:
    for path, data in files.items():
        safe_path(path)
        prior = previous.get(path)
        if path.exists() and prior is None:
            if regular_snapshot(path)[1] != data:
                raise ValueError(f"Agent changed after preflight: {path}")
            continue
        if prior is not None and regular_snapshot(path) != prior:
            raise ValueError(f"Agent changed after preflight: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".ams-install-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            info = Path(temporary).stat()
            identity = (info.st_dev, info.st_ino)
            if prior is None:
                # Create-only publication never overwrites another actor's file.
                os.link(temporary, path)
                created.append((path, identity, data))
            else:
                backup = backups / path.name
                # Take custody of the actual directory entry before trusting its
                # bytes. A copy followed by replacement can destroy a late edit.
                os.rename(path, backup)
                replaced.append((path, None, None, backup, prior))
                if regular_snapshot(backup) != prior:
                    raise ValueError(f"Agent changed during displacement: {path}")
                os.link(temporary, path)  # Never overwrite a newly appeared file.
                replaced[-1] = (path, identity, data, backup, prior)
        finally:
            Path(temporary).unlink(missing_ok=True)


def retire_native_files(agent_home: Path, harness: str, replaced: list[Replacement], backups: Path) -> None:
    for name in RETIRED_NATIVE_NAMES:
        path = agent_home / (name + ".md")
        # Unknown, custom, nonregular and redirected retired routes are untouched.
        try:
            safe_path(path)
            if not path.exists() or not path.is_file():
                continue
            prior = regular_snapshot(path)
        except ValueError:
            continue
        if predecessor_provider(name, prior[1], harness) is None:
            print(f"{harness}: preserving non-stock retired preset: {path}", flush=True)
            continue
        backup = backups / path.name
        os.rename(path, backup)
        replaced.append((path, None, None, backup, prior))
        if regular_snapshot(backup) != prior:
            raise ValueError(f"Retired agent changed during displacement: {path}")
        if path.exists() or path.is_symlink():
            raise ValueError(f"Retired agent removal failed: {path}")


def rollback(created: list[tuple[Path, tuple[int, int], bytes]], replaced: list[Replacement],
             backups: Path | None = None) -> bool:
    """Move before verifying; preserve actual displaced entries on every conflict.

    Restore is create-only. Private custody paths are retained if recovery is
    incomplete, including when a second actor recreates the live name.
    """
    complete = True
    for path, identity, data, backup, prior in (
            [(p, i, d, None, None) for p, i, d in reversed(created)] + list(reversed(replaced))):
        custody = None
        try:
            safe_path(path)
            if identity is not None and path.exists():
                if regular_snapshot(path) != (identity, data):
                    complete = False
                    continue
                directory = Path(tempfile.mkdtemp(prefix=".ams-rollback-", dir=backups or path.parent))
                custody = directory / path.name
                os.rename(path, custody)
                if regular_snapshot(custody) != (identity, data):
                    # A completed edit in the check/move window belongs to the
                    # user. Keep it at the live name if free, otherwise in custody.
                    os.link(custody, path)
                    complete = False
                    continue
            if backup is not None:
                safe_path(backup)
                os.link(backup, path)
            elif path.exists() or path.is_symlink():
                complete = False
            if custody is not None:
                custody.unlink()
                custody.parent.rmdir()
        except (OSError, ValueError):
            complete = False
    return complete


def stage_remote_package(root: Path) -> Path:
    manifest = remote_bytes("install-manifest.txt")
    entries = manifest_entries(manifest)
    (root / "install-manifest.txt").write_bytes(manifest)
    for name, (digest, length) in entries.items():
        data = remote_bytes(name)
        if len(data) != length or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"Package integrity check failed: {name}")
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    script_name = "install.ps1" if os.name == "nt" else "install.sh"
    script = root / script_name
    script.write_bytes(remote_bytes(script_name))
    if _remote_bytes("install-manifest.txt") != manifest:
        raise ValueError("Installation manifest changed during download; retry the install.")
    return script


def install_core(targets: set[str], env: dict[str, str], local: bool) -> None:
    if "codex" not in targets and env.get("AMS_INSTALL_PROFILES_ONLY") == "1":
        return
    native_env = env.copy()
    # The native installer runs from the package/staging directory, but custom
    # homes belong to the caller's cwd, including for a streamed bootstrap.
    for variable in (("AMS_SKILL_HOME", "CODEX_HOME") if "codex" in targets else ("AMS_SKILL_HOME",)):
        if native_env.get(variable):
            native_env[variable] = str(anchored_home(native_env[variable]))
    native_env.pop("AMS_INSTALL_SKILL_ONLY", None)
    if "codex" not in targets:
        native_env["AMS_INSTALL_SKILL_ONLY"] = "1"
    with tempfile.TemporaryDirectory(prefix="ams-bootstrap-") as temporary:
        package_root = ROOT if local else Path(temporary)
        script = (ROOT / ("install.ps1" if os.name == "nt" else "install.sh")
                  if local else stage_remote_package(package_root))
        if os.name == "nt":
            executable = shutil.which("powershell.exe")
            if not executable:
                raise ValueError("Windows PowerShell is required for the core installer.")
            command = [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Local"]
            native_env.pop("PSModulePath", None)
        else:
            command = ["bash", str(script), "--local"]
        subprocess.run(command, cwd=package_root, env=native_env, check=True, timeout=300)


def install(harness: str, opencode_provider: str = "auto", pi_provider: str = "auto",
            install_pi: bool = False, local: bool = True) -> int:
    targets = {"codex", "opencode", "pi"} if harness == "all" else {harness}
    if not targets <= {"codex", "opencode", "pi"}:
        raise ValueError("Unknown harness.")
    if install_pi and "pi" not in targets:
        raise ValueError("Installing pi-subagents requires the pi or all target.")
    env = os.environ.copy()
    if env.get("AMS_INSTALL_PROFILES_ONLY", "1") != "1":
        raise ValueError("AMS_INSTALL_PROFILES_ONLY must be unset or exactly 1.")
    providers = {"opencode": opencode_provider, "pi": pi_provider}
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", p) for p in providers.values()):
        raise ValueError("Invalid provider name.")
    homes = {}
    if "pi" in targets:
        homes["pi"] = home_path("PI_CODING_AGENT_DIR", Path.home() / ".pi/agent")
        env["PI_CODING_AGENT_DIR"] = str(homes["pi"])
    if "opencode" in targets:
        config = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config").expanduser()
        homes["opencode"] = home_path("OPENCODE_CONFIG_DIR", config / "opencode")
        env["OPENCODE_CONFIG_DIR"] = str(homes["opencode"])
    if {"pi", "opencode"} <= targets and homes["pi"] == homes["opencode"]:
        raise ValueError("OpenCode and Pi must have separate agent directories.")
    if "opencode" in targets:
        wait_for_opencode_desktop_exit(env)
    profiles = package_profiles(local) if targets - {"codex"} else []
    # Model catalogs do not control installation of the shared skill or Codex's registry.
    install_core(targets, env, local)
    if env.get("AMS_INSTALL_PROFILES_ONLY") != "1":
        skill = home_path("AMS_SKILL_HOME", Path.home() / ".agents/skills") / SKILL / "SKILL.md"
        print(f"Shared AMS skill installed: {skill}")
    if "codex" in targets:
        print("codex: skill/profile installation completed.")
    incomplete: list[str] = []
    for target in sorted(targets - {"codex"}):
        created: list[tuple[Path, tuple[int, int], bytes]] = []
        replaced: list[Replacement] = []
        cli_directory = None
        lock = None
        backups = None
        preserve_backups = False
        try:
            target_env = env.copy()
            if target == "opencode":
                cli_directory = tempfile.TemporaryDirectory(prefix="ams-opencode-cli-")
                target_env["AMS_OPENCODE_CLI"] = opencode_cli(target_env, Path(cli_directory.name))
                print(f"opencode: using CLI {target_env['AMS_OPENCODE_CLI']}", flush=True)
            models = catalog(target, target_env)
            pending_lock = native_lock(homes[target])
            pending_lock.__enter__()
            lock = pending_lock
            files = select_profiles(profiles, models, target, providers[target], homes[target] / "agents")
            previous = preflight(files)
            backups = Path(tempfile.mkdtemp(prefix=".ams-install-", dir=homes[target]))
            if target == "pi" and not pi_package(homes["pi"]):
                if not install_pi:
                    raise ValueError("Pi requires pi-subagents. Add --install-pi-subagents to permit its installation.")
                package_env = env.copy()
                cli("pi", ["install", "npm:pi-subagents"], env=package_env)
                if not pi_package(homes["pi"]):
                    raise RuntimeError("Pi did not register pi-subagents.")
            create_files(files, created, replaced, backups, previous)
            retire_native_files(homes[target] / "agents", target, replaced, backups)
            if target == "opencode":
                verify_opencode_agents(files, target_env)
                if running_opencode_desktops(target_env):
                    raise RuntimeError("Desktop was reopened during installation. Quit it normally and rerun so its server loads the installed agents.")
            preflight(files)
            if any(not p.is_file() or p.read_bytes() != data for p, data in files.items()):
                raise ValueError("Final native agent verification failed.")
            for path, _, published, backup, prior in replaced:
                if published is None and (path.exists() or path.is_symlink()):
                    raise ValueError(f"Retired agent reappeared before completion: {path}")
                if regular_snapshot(backup) != prior:
                    raise ValueError(f"Displaced agent changed before completion: {path}")
            print(f"{target}: {len(files)} native agent presets installed in {homes[target] / 'agents'}")
            if target == "opencode":
                print(f"opencode: all {len(files)} installed agents confirmed by the CLI registry.")
                print("opencode: installation finished. Open Desktop now to load these agents in a fresh server.")
            omitted = len(profiles) - len(files)
            if omitted:
                print(f"{target}: {omitted} presets omitted because their exact model IDs are not listed.")
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            preserve_backups = not rollback(created, replaced, backups)
            incomplete.append(target)
            print(f"{target}: NOT CONFIGURED: {error}", file=sys.stderr)
        except BaseException:
            preserve_backups = not rollback(created, replaced, backups)
            raise
        finally:
            if backups is not None:
                if preserve_backups:
                    print(f"{target}: incomplete recovery; displaced files and agent backups retained at {backups}", file=sys.stderr)
                else:
                    shutil.rmtree(backups)
            if lock is not None:
                lock.__exit__(None, None, None)
            if cli_directory is not None:
                cli_directory.cleanup()
    print("Restart the selected apps to reload skills and agents. In Codex type $ and select AMS.")
    print(f"Exact Codex skill name: ${SKILL}. Pi: /skill:{SKILL}.")
    print("Providers, credentials, permissions, compaction, and AMS project settings were not changed.")
    if incomplete:
        print(f"Partial installation: {', '.join(incomplete)} still need configuration. "
              "Successful targets and the shared skill were retained.", file=sys.stderr)
        return 2
    print("All selected targets installed. Model access and effective effort still depend on the harness/provider.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", choices=("codex", "opencode", "pi", "all"), required=True)
    parser.add_argument("--opencode-provider", default="auto", help="Provider ID, or auto (default).")
    parser.add_argument("--pi-provider", default="auto", help="Provider ID, or auto (default).")
    parser.add_argument("--install-pi-subagents", action="store_true")
    parser.add_argument("--local", action="store_true", help="Use the complete package beside this script instead of downloading.")
    args = parser.parse_args()
    try:
        return install(args.harness, args.opencode_provider, args.pi_provider,
                       args.install_pi_subagents, args.local)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
