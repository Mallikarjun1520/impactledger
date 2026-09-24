# ADR-012 — Base Sepolia MVP target

Status: Accepted
Date: 2026-09-24

## Context

We need a public, free, EVM-compatible chain for the anchor contract. The
choice must accept the $0 constraint (rulebook §24) and be replaceable
without domain rewrites (rulebook §22).

## Options considered

- Ethereum Sepolia — most portable, but faucet is stingy and gas is spiky.
- Base Sepolia — L2, cheap gas, reliable faucet, EVM identical, well
  supported by tooling.
- Optimism Sepolia — similar; slightly less mindshare.
- Polygon Amoy — cheap, but occasional reliability issues.

## Decision

Base Sepolia (chain id 84532) as the default. The anchor lives behind an
`AnchorAdapter` interface (`apps/api/app/services/anchor.py`), so switching
to any other EVM chain is a config change plus a redeploy of the same
Solidity contract.

## Reason

Cost, faucet reliability, EVM parity, adapter design keeps the choice
reversible.

## Consequences

- Easier: cheap and reliable demo.
- Harder: some auditors may prefer L1 finality. Mitigation: L2 finality is
  adequate for a transparency anchor whose value is timestamped commitment,
  not economic settlement.

## Revisit conditions

If Base Sepolia is deprecated by Coinbase, or if a partner insists on L1.
