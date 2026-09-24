// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ImpactAnchor
 * @notice Minimal cryptographic integrity anchor for ImpactLedger.
 *
 * Stores one Merkle root per batch. NO operational data. NO PII. The
 * platform pushes (batchId, merkleRoot, eventCount); anyone can read the
 * anchor back and verify a Merkle proof off-chain.
 *
 * Rulebook §22, Rule 04, Rule 05. See ADR-010 and ADR-011.
 */
contract ImpactAnchor {
    struct Anchor {
        bytes32 merkleRoot;
        uint32  eventCount;
        uint64  anchoredAt;
        address submitter;
    }

    /// @notice Optional operator restriction. Zero => open (any address may anchor).
    address public owner;
    mapping(address => bool) public submitters;
    bool public restricted;

    mapping(bytes16 => Anchor) private _anchors;

    event BatchAnchored(
        bytes16 indexed batchId,
        bytes32          merkleRoot,
        uint32           eventCount,
        address  indexed submitter
    );
    event SubmitterAllowed(address indexed submitter, bool allowed);
    event RestrictionSet(bool restricted);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    error NotOwner();
    error NotAllowedSubmitter();
    error AlreadyAnchored(bytes16 batchId);
    error ZeroBatchId();
    error ZeroRoot();
    error ZeroCount();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address _owner, bool _restricted) {
        owner = _owner;
        restricted = _restricted;
        emit OwnershipTransferred(address(0), _owner);
        emit RestrictionSet(_restricted);
    }

    function setRestricted(bool _restricted) external onlyOwner {
        restricted = _restricted;
        emit RestrictionSet(_restricted);
    }

    function setSubmitter(address who, bool allowed) external onlyOwner {
        submitters[who] = allowed;
        emit SubmitterAllowed(who, allowed);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        address prev = owner;
        owner = newOwner;
        emit OwnershipTransferred(prev, newOwner);
    }

    /**
     * @notice Anchor a new batch. The pair (batchId, merkleRoot) is written
     * once and cannot be overwritten. This is the entire operational surface.
     * @param batchId 128-bit id (typically a UUID emitted by the backend).
     * @param merkleRoot 32-byte RFC 6962 Merkle root of the batched event hashes.
     * @param eventCount number of leaves in the tree.
     */
    function anchorBatch(bytes16 batchId, bytes32 merkleRoot, uint32 eventCount) external {
        if (batchId == bytes16(0)) revert ZeroBatchId();
        if (merkleRoot == bytes32(0)) revert ZeroRoot();
        if (eventCount == 0) revert ZeroCount();
        if (restricted && !submitters[msg.sender]) revert NotAllowedSubmitter();
        if (_anchors[batchId].merkleRoot != bytes32(0)) revert AlreadyAnchored(batchId);

        _anchors[batchId] = Anchor({
            merkleRoot: merkleRoot,
            eventCount: eventCount,
            anchoredAt: uint64(block.timestamp),
            submitter:  msg.sender
        });

        emit BatchAnchored(batchId, merkleRoot, eventCount, msg.sender);
    }

    function getAnchor(bytes16 batchId) external view
        returns (bytes32 merkleRoot, uint32 eventCount, uint64 anchoredAt, address submitter)
    {
        Anchor storage a = _anchors[batchId];
        return (a.merkleRoot, a.eventCount, a.anchoredAt, a.submitter);
    }

    function isAnchored(bytes16 batchId) external view returns (bool) {
        return _anchors[batchId].merkleRoot != bytes32(0);
    }
}
