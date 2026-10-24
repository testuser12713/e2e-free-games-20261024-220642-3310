// The UI kit: presentational building blocks of the approved mockups
// (design/mockups/*.html). Screens compose these; they never re-implement them.
import './ui.css'

export { Button, LinkButton, buttonClassName } from './Button'
export type { ButtonProps, ButtonVariant, LinkButtonProps } from './Button'
export { PlatformBadge, FreeBadge } from './PlatformBadge'
export type { PlatformBadgeProps } from './PlatformBadge'
export { DealCard } from './DealCard'
export type { DealCardProps } from './DealCard'
export { DealCardSkeleton, Skeleton } from './DealCardSkeleton'
export type { SkeletonProps, SkeletonVariant } from './DealCardSkeleton'
export { SearchField } from './SearchField'
export type { SearchFieldProps } from './SearchField'
export { SelectField } from './SelectField'
export type { SelectFieldProps, SelectOption } from './SelectField'
export { PriceRangeField } from './PriceRangeField'
export type { PriceRange, PriceRangeFieldProps } from './PriceRangeField'
export { SegmentedField } from './SegmentedField'
export type { SegmentedFieldProps, SegmentedOption } from './SegmentedField'
export { StatusPill, PillList } from './StatusPill'
export type { PillListProps, PillStatus, StatusPillProps } from './StatusPill'
export { Progress } from './Progress'
export type { ProgressProps } from './Progress'
export { InlineNotice } from './InlineNotice'
export type { InlineNoticeProps, NoticeTone } from './InlineNotice'
export { EmptyState } from './EmptyState'
export type { EmptyStateProps, EmptyStateVariant } from './EmptyState'
export { ErrorState } from './ErrorState'
export type { ErrorStateProps } from './ErrorState'
export { Prose, ProseSection, DataList, TodoMark, Table } from './Prose'
export type { DataListItem, ProseProps, ProseSectionProps, TableProps } from './Prose'
export { Icon } from './icons'
export type { IconName, IconProps } from './icons'
export {
  calendarDaysBetween,
  formatDateTime,
  formatPrice,
  formatTimeLeft,
  isSafeHttpUrl,
  parseDate,
} from './format'
