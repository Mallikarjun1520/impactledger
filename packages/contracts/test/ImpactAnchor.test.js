const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ImpactAnchor", function () {
  async function deploy(restricted = false) {
    const [owner, other] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("ImpactAnchor");
    const contract = await Factory.deploy(owner.address, restricted);
    await contract.waitForDeployment();
    return { contract, owner, other };
  }

  function batchId(n) {
    const hex = n.toString(16).padStart(32, "0");
    return "0x" + hex;
  }

  function root(seed) {
    return ethers.keccak256(ethers.toUtf8Bytes("root-" + seed));
  }

  it("anchors a batch and emits an event", async function () {
    const { contract, owner } = await deploy();
    const id = batchId(1);
    const r = root("a");

    await expect(contract.anchorBatch(id, r, 7))
      .to.emit(contract, "BatchAnchored")
      .withArgs(id, r, 7, owner.address);

    const [merkleRoot, eventCount, anchoredAt, submitter] = await contract.getAnchor(id);
    expect(merkleRoot).to.equal(r);
    expect(eventCount).to.equal(7);
    expect(submitter).to.equal(owner.address);
    expect(anchoredAt).to.be.greaterThan(0n);
    expect(await contract.isAnchored(id)).to.equal(true);
  });

  it("rejects a duplicate batch id", async function () {
    const { contract } = await deploy();
    const id = batchId(2);
    await contract.anchorBatch(id, root("first"), 1);
    await expect(contract.anchorBatch(id, root("second"), 1))
      .to.be.revertedWithCustomError(contract, "AlreadyAnchored");
  });

  it("rejects zero inputs", async function () {
    const { contract } = await deploy();
    const goodId = batchId(3);
    await expect(contract.anchorBatch(ethers.ZeroHash.slice(0, 34), root("x"), 1))
      .to.be.revertedWithCustomError(contract, "ZeroBatchId");
    await expect(contract.anchorBatch(goodId, ethers.ZeroHash, 1))
      .to.be.revertedWithCustomError(contract, "ZeroRoot");
    await expect(contract.anchorBatch(goodId, root("x"), 0))
      .to.be.revertedWithCustomError(contract, "ZeroCount");
  });

  it("enforces restricted submitters when enabled", async function () {
    const { contract, owner, other } = await deploy(true);
    const id = batchId(4);
    await expect(contract.connect(other).anchorBatch(id, root("x"), 1))
      .to.be.revertedWithCustomError(contract, "NotAllowedSubmitter");
    await contract.connect(owner).setSubmitter(other.address, true);
    await expect(contract.connect(other).anchorBatch(id, root("x"), 1))
      .to.emit(contract, "BatchAnchored");
  });

  it("only owner can flip restriction and manage submitters", async function () {
    const { contract, other } = await deploy();
    await expect(contract.connect(other).setRestricted(true))
      .to.be.revertedWithCustomError(contract, "NotOwner");
    await expect(contract.connect(other).setSubmitter(other.address, true))
      .to.be.revertedWithCustomError(contract, "NotOwner");
    await expect(contract.connect(other).transferOwnership(other.address))
      .to.be.revertedWithCustomError(contract, "NotOwner");
  });
});
