'use strict';

// Electron exposes the index on the event; older builds also pass it separately.
// An unknown index must never turn an Approve click into Deny.
function approvalDecision(details, legacyIndex) {
  const index = [details?.actionIndex, legacyIndex].find(value => value === 0 || value === 1);
  return index === 0 ? true : index === 1 ? false : null;
}

module.exports = { approvalDecision };
