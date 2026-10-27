// Shared helpers for ballot status + countdown.

// A ballot is effectively "closed" if its status is closed OR its end_date has passed.
export function getEffectiveStatus(ballot, now = new Date()) {
  if (!ballot) return 'closed';
  if (ballot.status === 'closed') return 'closed';
  if (ballot.end_date && new Date(ballot.end_date) <= now) return 'closed';
  return 'open';
}

// Human-readable time left, e.g. "3d 4h left", "5h 12m left", "8m left", "Ended".
export function formatTimeRemaining(endDate, now = new Date()) {
  if (!endDate) return '';
  const diffMs = new Date(endDate) - now;
  if (diffMs <= 0) return 'Ended';

  const totalMinutes = Math.floor(diffMs / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;

  if (days > 0) return `${days}d ${hours}h left`;
  if (hours > 0) return `${hours}h ${minutes}m left`;
  return `${minutes}m left`;
}

// True when an open ballot ends within the next 24 hours.
export function isEndingSoon(endDate, now = new Date()) {
  if (!endDate) return false;
  const diffMs = new Date(endDate) - now;
  return diffMs > 0 && diffMs <= 24 * 60 * 60 * 1000;
}

// Ballot categories (must match Ballot.CATEGORY_CHOICES on the backend).
export const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "music", label: "Music" },
  { value: "gaming", label: "Gaming" },
  { value: "sports", label: "Sports" },
  { value: "technology", label: "Technology" },
  { value: "food", label: "Food" },
  { value: "travel", label: "Travel" },
  { value: "movies", label: "Movies" },
  { value: "other", label: "Other" },
];

export function categoryLabel(value) {
  const c = CATEGORIES.find(x => x.value === value);
  return c ? c.label : "General";
}
