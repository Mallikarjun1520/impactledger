class ImpactLedgerError(Exception):
    """Base exception for ImpactLedger domain errors."""
    pass


class LastAdminError(ImpactLedgerError):
    """Raised when an operation would leave an organization without an admin."""
    pass


class DuplicateSlugError(ImpactLedgerError):
    """Raised when an organization slug already exists."""
    pass


class MemberAlreadyExistsError(ImpactLedgerError):
    """Raised when a user is already a member of an organization."""
    pass


class OrganizationNotFoundError(ImpactLedgerError):
    """Raised when an organization is not found."""
    pass


class MemberNotFoundError(ImpactLedgerError):
    """Raised when a member is not found in an organization."""
    pass


class DuplicateResourceTypeError(ImpactLedgerError):
    """Raised when a resource type name already exists within an organization."""
    pass


class ResourceTypeNotFoundError(ImpactLedgerError):
    """Raised when a resource type is not found."""
    pass


class DuplicateBatchCodeError(ImpactLedgerError):
    """Raised when a batch code already exists within an organization."""
    pass


class ResourceBatchNotFoundError(ImpactLedgerError):
    """Raised when a resource batch is not found."""
    pass


class InsufficientInventoryError(ImpactLedgerError):
    """Raised when an operation requires more inventory than available."""
    pass


class ContributionNotFoundError(ImpactLedgerError):
    """Raised when a contribution is not found."""
    pass


class AllocationNotFoundError(ImpactLedgerError):
    """Raised when an allocation is not found."""
    pass


class InvalidAllocationError(ImpactLedgerError):
    """Raised when an allocation is invalid, e.g. exceeds available contribution amount."""
    pass


class CrossTenantAccessError(ImpactLedgerError):
    """Raised when an operation attempts to access an entity across tenant boundaries."""
    pass
