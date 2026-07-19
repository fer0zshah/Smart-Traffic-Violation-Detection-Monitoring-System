<x-app-layout>
    <x-slot name="header">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <h2 class="text-2xl font-bold leading-tight text-slate-900">Traffic violation dashboard</h2>
                <p class="mt-1 text-sm text-slate-500">
                    Evidence analytics for {{ auth()->user()->name }}
                    <span class="ml-2 rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold uppercase text-slate-700">
                        {{ auth()->user()->role }}
                    </span>
                </p>
            </div>
            <a href="{{ route('violations.index') }}" class="inline-flex items-center justify-center rounded-lg bg-red-700 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-800">
                Open violation register
            </a>
        </div>
    </x-slot>

    <div class="py-8">
        <div class="mx-auto max-w-7xl space-y-6 px-4 sm:px-6 lg:px-8">
            <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                    <p class="text-sm font-medium text-slate-500">Total evidence</p>
                    <p class="mt-2 text-3xl font-bold text-slate-950">{{ $total }}</p>
                    <p class="mt-1 text-xs text-slate-500">All stored violation records</p>
                </div>

                <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                    <p class="text-sm font-medium text-slate-500">Today</p>
                    <p class="mt-2 text-3xl font-bold text-red-700">{{ $todayCount }}</p>
                    <p class="mt-1 text-xs text-slate-500">Captured today</p>
                </div>

                <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                    <p class="text-sm font-medium text-slate-500">Pending review</p>
                    <p class="mt-2 text-3xl font-bold text-amber-600">{{ $pendingCount }}</p>
                    <p class="mt-1 text-xs text-slate-500">Need officer confirmation</p>
                </div>

                <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
                    <p class="text-sm font-medium text-slate-500">OCR attention</p>
                    <p class="mt-2 text-3xl font-bold text-slate-950">{{ $unreadableCount + $lowConfidenceCount }}</p>
                    <p class="mt-1 text-xs text-slate-500">{{ $unreadableCount }} unreadable, {{ $lowConfidenceCount }} low confidence</p>
                </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-3">
                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 xl:col-span-2">
                    <div class="flex items-center justify-between">
                        <div>
                            <h3 class="text-lg font-bold text-slate-900">Last 7 days</h3>
                            <p class="text-sm text-slate-500">Violation volume by capture date</p>
                        </div>
                    </div>

                    <div class="mt-6 grid h-56 grid-cols-7 items-end gap-3">
                        @foreach ($dailyTrend as $day)
                            <div class="flex h-full flex-col items-center justify-end gap-2">
                                <div class="text-xs font-semibold text-slate-700">{{ $day['count'] }}</div>
                                <div
                                    class="w-full rounded-t-xl bg-red-600"
                                    style="height: {{ max(8, ($day['count'] / $maxDailyCount) * 180) }}px"
                                    title="{{ $day['date'] }}: {{ $day['count'] }}"
                                ></div>
                                <div class="text-center">
                                    <p class="text-xs font-semibold text-slate-700">{{ $day['label'] }}</p>
                                    <p class="text-[11px] text-slate-400">{{ $day['date'] }}</p>
                                </div>
                            </div>
                        @endforeach
                    </div>
                </div>

                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                    <h3 class="text-lg font-bold text-slate-900">Review status</h3>
                    <p class="text-sm text-slate-500">Officer workflow progress</p>

                    <div class="mt-5 space-y-4">
                        @foreach ($statusBreakdown as $status)
                            <div>
                                <div class="mb-1 flex items-center justify-between text-sm">
                                    <span class="font-semibold text-slate-700">{{ $status['label'] }}</span>
                                    <span class="text-slate-500">{{ $status['count'] }} / {{ $status['percentage'] }}%</span>
                                </div>
                                <div class="h-3 overflow-hidden rounded-full bg-slate-100">
                                    <div class="h-full {{ $status['color'] }}" style="width: {{ $status['percentage'] }}%"></div>
                                </div>
                            </div>
                        @endforeach
                    </div>
                </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-3">
                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                    <h3 class="text-lg font-bold text-slate-900">Violation type</h3>
                    <p class="text-sm text-slate-500">Red light vs overspeed split</p>

                    <div class="mt-5 space-y-4">
                        @forelse ($typeBreakdown as $type)
                            <div>
                                <div class="mb-1 flex items-center justify-between text-sm">
                                    <span class="font-semibold text-slate-700">{{ $type['label'] }}</span>
                                    <span class="text-slate-500">{{ $type['count'] }}</span>
                                </div>
                                <div class="h-3 overflow-hidden rounded-full bg-slate-100">
                                    <div class="h-full rounded-full bg-red-600" style="width: {{ $type['percentage'] }}%"></div>
                                </div>
                            </div>
                        @empty
                            <p class="text-sm text-slate-500">No violation type data yet.</p>
                        @endforelse
                    </div>
                </div>

                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                    <h3 class="text-lg font-bold text-slate-900">Peak hours</h3>
                    <p class="text-sm text-slate-500">Busiest violation capture times</p>

                    <div class="mt-5 space-y-3">
                        @forelse ($peakHours as $hour)
                            <div class="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                                <span class="font-semibold text-slate-800">{{ $hour['hour'] }}</span>
                                <span class="rounded-full bg-red-100 px-3 py-1 text-sm font-bold text-red-700">{{ $hour['count'] }}</span>
                            </div>
                        @empty
                            <p class="text-sm text-slate-500">No hourly data yet.</p>
                        @endforelse
                    </div>
                </div>

                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                    <h3 class="text-lg font-bold text-slate-900">Top repeated plates</h3>
                    <p class="text-sm text-slate-500">Vehicles with multiple records</p>

                    <div class="mt-5 space-y-3">
                        @forelse ($topPlates as $plate)
                            <div class="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                                <span class="font-semibold text-slate-800">{{ $plate['plate'] }}</span>
                                <span class="rounded-full bg-slate-900 px-3 py-1 text-sm font-bold text-white">{{ $plate['count'] }}</span>
                            </div>
                        @empty
                            <p class="text-sm text-slate-500">No repeated readable plate yet.</p>
                        @endforelse
                    </div>
                </div>
            </div>

            <div class="grid gap-6 xl:grid-cols-3">
                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                    <h3 class="text-lg font-bold text-slate-900">Vehicle colors</h3>
                    <p class="text-sm text-slate-500">Most common detected colors</p>

                    <div class="mt-5 space-y-3">
                        @forelse ($colorBreakdown as $color)
                            <div class="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                                <span class="font-semibold text-slate-800">{{ $color['color'] }}</span>
                                <span class="text-sm font-bold text-slate-700">{{ $color['count'] }}</span>
                            </div>
                        @empty
                            <p class="text-sm text-slate-500">No color data yet.</p>
                        @endforelse
                    </div>
                </div>

                <div class="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 xl:col-span-2">
                    <div class="flex items-center justify-between gap-4">
                        <div>
                            <h3 class="text-lg font-bold text-slate-900">Latest evidence</h3>
                            <p class="text-sm text-slate-500">Newest records from the detection pipeline</p>
                        </div>
                        <a href="{{ route('violations.index') }}" class="text-sm font-semibold text-red-700 hover:text-red-900">View all</a>
                    </div>

                    <div class="mt-5 overflow-hidden rounded-xl border border-slate-200">
                        <table class="min-w-full divide-y divide-slate-200">
                            <thead class="bg-slate-50">
                                <tr>
                                    <th class="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Evidence</th>
                                    <th class="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Plate</th>
                                    <th class="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Type</th>
                                    <th class="px-4 py-3 text-left text-xs font-bold uppercase tracking-wide text-slate-500">Status</th>
                                    <th class="px-4 py-3 text-right text-xs font-bold uppercase tracking-wide text-slate-500">Action</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 bg-white">
                                @forelse ($latestViolations as $violation)
                                    <tr>
                                        <td class="px-4 py-3">
                                            @if ($violation->image_path)
                                                <img src="{{ asset('storage/'.$violation->image_path) }}" alt="Violation evidence" class="h-12 w-16 rounded-lg object-cover ring-1 ring-slate-200">
                                            @else
                                                <div class="flex h-12 w-16 items-center justify-center rounded-lg bg-slate-100 text-xs text-slate-400">No img</div>
                                            @endif
                                        </td>
                                        <td class="px-4 py-3">
                                            <p class="font-semibold text-slate-900">{{ $violation->plate_number }}</p>
                                            <p class="text-xs text-slate-500">{{ $violation->frame_timestamp?->format('M d, Y h:i A') ?? 'No timestamp' }}</p>
                                        </td>
                                        <td class="px-4 py-3 text-sm font-medium text-slate-700">{{ str_replace('_', ' ', $violation->violation_type) }}</td>
                                        <td class="px-4 py-3">
                                            <span class="rounded-full px-2.5 py-1 text-xs font-bold
                                                @class([
                                                    'bg-amber-100 text-amber-700' => $violation->status === 'PENDING',
                                                    'bg-emerald-100 text-emerald-700' => $violation->status === 'CONFIRMED',
                                                    'bg-slate-100 text-slate-700' => $violation->status === 'DISMISSED',
                                                ])">
                                                {{ $violation->status }}
                                            </span>
                                        </td>
                                        <td class="px-4 py-3 text-right">
                                            <a href="{{ route('violations.show', $violation) }}" class="font-semibold text-red-700 hover:text-red-900">Review</a>
                                        </td>
                                    </tr>
                                @empty
                                    <tr>
                                        <td colspan="5" class="px-4 py-8 text-center text-sm text-slate-500">No violation evidence stored yet.</td>
                                    </tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</x-app-layout>
