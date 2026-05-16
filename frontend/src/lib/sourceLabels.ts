export function sourceTypeLabel(sourceType?: string | null) {
  const normalized = normalizeSourceType(sourceType);
  if (!normalized) return undefined;
  if (normalized === "gmail" || normalized === "gmail_attachment") return "Mail";
  if (normalized === "drive") return "Docs";
  if (normalized === "calendar") return "Calendar";
  if (normalized === "slack") return "Slack";
  return sourceType?.trim() || undefined;
}

export function sourceFamilyLabel(sourceTypes: readonly unknown[]) {
  const labels = sourceTypes
    .map((sourceType) => (typeof sourceType === "string" ? sourceTypeLabel(sourceType) : undefined))
    .filter((label): label is string => Boolean(label));
  const orderedLabels = ["Mail", "Docs", "Calendar", "Slack"].filter((label) => labels.includes(label));
  const otherLabels = labels.filter((label) => !orderedLabels.includes(label));
  const uniqueLabels = [...orderedLabels, ...otherLabels].filter((label, index, list) => list.indexOf(label) === index);
  return uniqueLabels.length > 0 ? uniqueLabels.join(" + ") : undefined;
}

export function sourceTypeFromUrl(url?: string | null) {
  const lowered = url?.toLowerCase() || "";
  if (!lowered) return undefined;
  if (lowered.includes("mail.google.com") || lowered.includes("gmail.")) return "gmail";
  if (lowered.includes("drive.google.com") || lowered.includes("drive.")) return "drive";
  if (lowered.includes("calendar.google.com") || lowered.includes("calendar.")) return "calendar";
  if (lowered.includes("slack.com") || lowered.includes("slack.")) return "slack";
  return undefined;
}

function normalizeSourceType(sourceType?: string | null) {
  const normalized = sourceType?.trim().toLowerCase();
  return normalized || undefined;
}
