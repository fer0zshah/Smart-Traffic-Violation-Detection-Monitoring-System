<?php

namespace App\Http\Controllers;

use App\Models\Violation;
use Carbon\CarbonImmutable;
use Illuminate\Contracts\View\View;

class DashboardController extends Controller
{
    public function __invoke(): View
    {
        $violations = Violation::query()
            ->select([
                'id',
                'event_id',
                'plate_number',
                'violation_type',
                'status',
                'vehicle_color',
                'ocr_confidence',
                'frame_timestamp',
                'image_path',
                'speed',
                'speed_limit',
            ])
            ->latest('frame_timestamp')
            ->get();

        $today = CarbonImmutable::today();
        $lastSevenDays = collect(range(6, 0))
            ->map(fn (int $daysAgo): CarbonImmutable => $today->subDays($daysAgo));

        $total = $violations->count();
        $todayCount = $violations
            ->filter(fn (Violation $violation): bool => $violation->frame_timestamp?->isSameDay($today) ?? false)
            ->count();

        $pendingCount = $violations->where('status', 'PENDING')->count();
        $confirmedCount = $violations->where('status', 'CONFIRMED')->count();
        $dismissedCount = $violations->where('status', 'DISMISSED')->count();
        $unreadableCount = $violations
            ->filter(fn (Violation $violation): bool => strtoupper((string) $violation->plate_number) === 'UNREADABLE')
            ->count();

        $typeBreakdown = $violations
            ->groupBy('violation_type')
            ->map(fn ($items, string $type): array => [
                'label' => str_replace('_', ' ', $type),
                'count' => $items->count(),
                'percentage' => $total > 0 ? round(($items->count() / $total) * 100) : 0,
            ])
            ->sortByDesc('count')
            ->values();

        $statusBreakdown = collect([
            ['label' => 'Pending', 'count' => $pendingCount, 'color' => 'bg-amber-500'],
            ['label' => 'Confirmed', 'count' => $confirmedCount, 'color' => 'bg-emerald-500'],
            ['label' => 'Dismissed', 'count' => $dismissedCount, 'color' => 'bg-slate-500'],
        ])->map(fn (array $row): array => [
            ...$row,
            'percentage' => $total > 0 ? round(($row['count'] / $total) * 100) : 0,
        ]);

        $dailyTrend = $lastSevenDays->map(function (CarbonImmutable $date) use ($violations): array {
            return [
                'label' => $date->format('D'),
                'date' => $date->format('M d'),
                'count' => $violations
                    ->filter(fn (Violation $violation): bool => $violation->frame_timestamp?->isSameDay($date) ?? false)
                    ->count(),
            ];
        });

        $maxDailyCount = max(1, (int) $dailyTrend->max('count'));

        $peakHours = $violations
            ->filter(fn (Violation $violation): bool => $violation->frame_timestamp !== null)
            ->groupBy(fn (Violation $violation): string => $violation->frame_timestamp->format('H:00'))
            ->map(fn ($items, string $hour): array => [
                'hour' => $hour,
                'count' => $items->count(),
            ])
            ->sortByDesc('count')
            ->take(5)
            ->values();

        $topPlates = $violations
            ->filter(fn (Violation $violation): bool => filled($violation->plate_number)
                && strtoupper((string) $violation->plate_number) !== 'UNREADABLE')
            ->groupBy('plate_number')
            ->map(fn ($items, string $plate): array => [
                'plate' => $plate,
                'count' => $items->count(),
            ])
            ->sortByDesc('count')
            ->take(5)
            ->values();

        $colorBreakdown = $violations
            ->filter(fn (Violation $violation): bool => filled($violation->vehicle_color))
            ->groupBy('vehicle_color')
            ->map(fn ($items, string $color): array => [
                'color' => $color,
                'count' => $items->count(),
            ])
            ->sortByDesc('count')
            ->take(5)
            ->values();

        $lowConfidenceCount = $violations
            ->filter(fn (Violation $violation): bool => ($violation->ocr_confidence ?? 0) > 0
                && ($violation->ocr_confidence ?? 0) < 0.60)
            ->count();

        $latestViolations = $violations->take(6);

        return view('dashboard', compact(
            'colorBreakdown',
            'confirmedCount',
            'dailyTrend',
            'dismissedCount',
            'latestViolations',
            'lowConfidenceCount',
            'maxDailyCount',
            'peakHours',
            'pendingCount',
            'statusBreakdown',
            'todayCount',
            'topPlates',
            'total',
            'typeBreakdown',
            'unreadableCount',
        ));
    }
}
