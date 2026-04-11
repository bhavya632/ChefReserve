export default function MatchBadge({ percent }) {
  const color =
    percent >= 90 ? "bg-green-100 text-green-700" :
    percent >= 70 ? "bg-amber-100 text-amber-700" :
    "bg-orange-100 text-orange-700";

  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>
      {percent}% match
    </span>
  );
}
