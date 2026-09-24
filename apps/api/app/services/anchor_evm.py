"""EVM anchor adapter (ADR-012, Base Sepolia by default).

The contract ABI matches ``packages/contracts/contracts/ImpactAnchor.sol``.
Only the function we call is included; the full ABI ships with the frontend
verifier.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from eth_account import Account
from web3 import Web3
from web3.exceptions import Web3Exception
from web3.middleware import ExtraDataToPOAMiddleware

from app.services.anchor import AnchorReceipt, AnchorRequest


log = logging.getLogger(__name__)


ANCHOR_ABI = [
    {
        "inputs": [
            {"internalType": "bytes16", "name": "batchId", "type": "bytes16"},
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "uint32", "name": "eventCount", "type": "uint32"},
        ],
        "name": "anchorBatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes16", "name": "batchId", "type": "bytes16"}],
        "name": "getAnchor",
        "outputs": [
            {"internalType": "bytes32", "name": "merkleRoot", "type": "bytes32"},
            {"internalType": "uint32", "name": "eventCount", "type": "uint32"},
            {"internalType": "uint64", "name": "anchoredAt", "type": "uint64"},
            {"internalType": "address", "name": "submitter", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True,  "name": "batchId", "type": "bytes16"},
            {"indexed": False, "name": "merkleRoot", "type": "bytes32"},
            {"indexed": False, "name": "eventCount", "type": "uint32"},
            {"indexed": True,  "name": "submitter", "type": "address"},
        ],
        "name": "BatchAnchored",
        "type": "event",
    },
]


def _uuid_to_bytes16(uuid_str: str) -> bytes:
    """Pack a UUID's 128 bits into a ``bytes16`` value."""
    hex_only = uuid_str.replace("-", "")
    return bytes.fromhex(hex_only)


@dataclass
class EvmAnchorAdapter:
    rpc_url: str
    chain_id: int
    contract_address: str
    private_key: str

    def _client(self) -> Web3:
        w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={"timeout": 20}))
        # Base Sepolia uses POA-style consensus for its extraData block field.
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        if not w3.is_connected():
            raise RuntimeError(f"Anchor RPC unreachable: {self.rpc_url}")
        return w3

    def submit(self, request: AnchorRequest) -> AnchorReceipt:
        w3 = self._client()
        acct = Account.from_key(self.private_key)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=ANCHOR_ABI,
        )

        tx = contract.functions.anchorBatch(
            _uuid_to_bytes16(str(request.batch_id)),
            bytes.fromhex(request.merkle_root_hex),
            request.event_count,
        ).build_transaction({
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": self.chain_id,
            # EIP-1559 defaults; Base Sepolia is friendly.
            "maxFeePerGas": w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": w3.to_wei("0.1", "gwei"),
        })

        try:
            gas_estimate = w3.eth.estimate_gas(tx)
            tx["gas"] = int(gas_estimate * 1.2)
        except Web3Exception as e:
            log.warning("Gas estimate failed, falling back to 150k: %s", e)
            tx["gas"] = 150_000

        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
        if not tx_hash.startswith("0x"):
            tx_hash = "0x" + tx_hash

        return AnchorReceipt(
            tx_hash=tx_hash,
            block_number=None,
            chain_id=self.chain_id,
            contract_address=self.contract_address,
        )

    def confirmed(self, receipt: AnchorReceipt, min_confirmations: int) -> bool:
        w3 = self._client()
        try:
            r = w3.eth.get_transaction_receipt(receipt.tx_hash)
        except Web3Exception:
            return False
        if not r or r.blockNumber is None:
            return False
        head = w3.eth.block_number
        return (head - r.blockNumber + 1) >= min_confirmations
