"""Shared test fixtures for the NMAxe integration."""

from __future__ import annotations

from typing import Any

from custom_components.nmaxe.models import (
    build_unique_id,
    parse_pool_config,
    parse_system_info,
)

HOST = "192.168.1.100"
ENTITY_URL = f"http://{HOST}"
SECRET = "super-secret-pool-password"

SYSTEM_INFO_PAYLOAD: dict[str, Any] = {
    "power": {
        "power": 25.4,
        "vbus": 12000,
        "ibus": 2116,
    },
    "temps": {
        "vcore": 45.2,
        "asic": 62.7,
    },
    "asic": {
        "count": 1,
        "model": "BM1370",
        "vcoreReq": 1125,
        "vcoreReal": 1123,
        "freqReq": 600,
        "smallCoreCnt": 672,
    },
    "miner": {
        "state": "running",
        "paused": False,
        "pauseReason": "",
        "hashRate": 1200.5,
        "bestDiffEver": "1.23M",
        "bestDiffSession": "456.7K",
        "networkDiff": "88.55T",
        "poolDiff": "65536",
        "lastDiff": "131072",
        "blkhits": 2,
        "freeHeap": 187320,
        "minFreeHeap": 163840,
        "sAccepted": 1024,
        "sRejected": 3,
        "uptimeSeconds": 86400,
        "uptimeEver": 2592000,
        "bmMode": 0,
    },
    "identity": {
        "fwVersion": "v3.2.01",
        "hwModel": "NMAxeGamma",
        "displayName": "NMAxeGamma",
        "hostName": "nmaxe-gamma-01",
        "ssid": "HomeNet",
        "rssi": -55,
        "appSha256": "ef970b389312276b",
    },
    "fans": [
        {
            "id": 0,
            "speed": 60,
            "rpm": 2800,
        }
    ],
    "stratum": {
        "url": "stratum+tcp://pool.example.com:3333",
        "user": "bc1qexample.worker1",
        "pwd": SECRET,
    },
}

POOL_CONFIG_PAYLOAD: dict[str, Any] = {
    "vcoreReq": 1125,
    "freqReq": 600,
    "asic": "BM1370",
    "stratum": {
        "used": {
            "url": "stratum+tcp://pool.example.com:3333",
            "user": "bc1qexample.worker1",
            "pwd": SECRET,
        },
        "primary": {
            "url": "stratum+tcp://pool.example.com:3333",
            "user": "bc1qexample.worker1",
            "pwd": SECRET,
        },
        "fallback": {
            "url": "stratum+tcp://fallback.example.com:3333",
            "user": "bc1qexample.worker1",
            "pwd": SECRET,
        },
    },
}

SYSTEM_INFO = parse_system_info(SYSTEM_INFO_PAYLOAD)
POOL_CONFIG = parse_pool_config(POOL_CONFIG_PAYLOAD)
UNIQUE_ID = build_unique_id(SYSTEM_INFO.identity)
