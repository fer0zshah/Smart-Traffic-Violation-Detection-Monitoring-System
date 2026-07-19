<x-app-layout>
    <x-slot name="header">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <a href="{{ route('violations.index') }}" class="text-sm font-semibold text-red-700 hover:text-red-900">← Back to violations</a>
                <h2 class="mt-1 text-2xl font-bold text-slate-900">Violation evidence</h2>
                <p class="font-mono text-xs text-slate-500">{{ $violation->event_id }}</p>
            </div>
            <span class="inline-flex self-start rounded-full px-3 py-1.5 text-xs font-bold uppercase tracking-wide {{ match($violation->status) {
                'CONFIRMED' => 'bg-emerald-100 text-emerald-800',
                'DISMISSED' => 'bg-slate-200 text-slate-700',
                default => 'bg-indigo-100 text-indigo-800',
            } }}">{{ $violation->status }}</span>
        </div>
    </x-slot>

    <div class="py-8">
        <div class="mx-auto max-w-7xl space-y-6 px-4 sm:px-6 lg:px-8">
            @if (session('status'))
                <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800">
                    {{ session('status') }}
                </div>
            @endif

            <div class="grid gap-6 xl:grid-cols-3">
                <div class="space-y-6 xl:col-span-2">
                    <section class="overflow-hidden rounded-xl border border-slate-200 bg-slate-950 shadow-sm">
                        <div class="flex items-center justify-between border-b border-white/10 px-5 py-3 text-white">
                            <h3 class="font-semibold">Violation frame</h3>
                            <span class="text-xs text-slate-300">Frame {{ number_format($violation->frame_number) }}</span>
                        </div>
                        @if ($violation->image_path)
                            <a href="{{ asset('storage/'.$violation->image_path) }}" target="_blank" rel="noopener">
                                <img src="{{ asset('storage/'.$violation->image_path) }}" alt="Full violation evidence for {{ $violation->event_id }}"
                                     class="max-h-[640px] w-full object-contain">
                            </a>
                        @else
                            <div class="flex min-h-80 items-center justify-center text-sm text-slate-400">No full-frame evidence available</div>
                        @endif
                    </section>

                    @php
                        $evidenceImages = $violation->evidence_images ?? [];
                        $plateImages = array_values(array_filter($evidenceImages, fn ($sample) => !empty($sample['plate_path'])));
                    @endphp
                    @if (count($evidenceImages))
                        <div class="space-y-6">
                            <h3 class="sr-only">Tracked evidence sequence</h3>

                            <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                                <div class="flex items-center justify-between gap-4">
                                    <div>
                                        <h3 class="text-lg font-bold text-slate-900">Vehicle images</h3>
                                        <p class="mt-1 text-sm text-slate-500">Tracked vehicle crops captured until it left the frame.</p>
                                    </div>
                                    <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{{ count($evidenceImages) }} images</span>
                                </div>
                                <div class="mt-5 grid gap-4 sm:grid-cols-2">
                                    @foreach ($evidenceImages as $sample)
                                        <article class="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                                            <div class="px-3 py-2 text-xs text-slate-500">Frame {{ number_format($sample['frame_number'] ?? 0) }}</div>
                                            @if (!empty($sample['vehicle_path']))
                                                <a href="{{ asset('storage/'.$sample['vehicle_path']) }}" target="_blank" rel="noopener">
                                                    <img src="{{ asset('storage/'.$sample['vehicle_path']) }}" alt="Vehicle sample at frame {{ $sample['frame_number'] ?? 0 }}" class="h-48 w-full bg-slate-900 object-contain">
                                                </a>
                                            @endif
                                        </article>
                                    @endforeach
                                </div>
                            </section>

                            <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                                <div class="flex items-center justify-between gap-4">
                                    <div>
                                        <h3 class="text-lg font-bold text-slate-900">Plate images</h3>
                                        <p class="mt-1 text-sm text-slate-500">Localized plate crops with their individual OCR results.</p>
                                    </div>
                                    <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{{ count($plateImages) }} images</span>
                                </div>
                                <div class="mt-5 grid gap-4 sm:grid-cols-2">
                                    @forelse ($plateImages as $sample)
                                        <article class="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                                            <div class="flex items-center justify-between px-3 py-2 text-xs text-slate-500">
                                                <span>Frame {{ number_format($sample['frame_number'] ?? 0) }}</span>
                                                <span>{{ number_format(($sample['ocr_confidence'] ?? 0) * 100, 1) }}% {{ $sample['ocr_engine'] ?? 'none' }}</span>
                                            </div>
                                            <div class="space-y-2 p-3">
                                                <a href="{{ asset('storage/'.$sample['plate_path']) }}" target="_blank" rel="noopener">
                                                    <img src="{{ asset('storage/'.$sample['plate_path']) }}" alt="Plate sample at frame {{ $sample['frame_number'] ?? 0 }}" class="h-24 w-full rounded bg-white object-contain ring-1 ring-slate-200">
                                                </a>
                                                <p class="break-words text-xs text-slate-600">OCR: {{ $sample['ocr_text'] ?: 'No text detected' }}</p>
                                                <p class="text-xs font-semibold {{ ($sample['plate_number'] ?? 'UNREADABLE') === 'UNREADABLE' ? 'text-red-700' : 'text-emerald-700' }}">{{ $sample['plate_number'] ?? 'UNREADABLE' }}</p>
                                            </div>
                                        </article>
                                    @empty
                                        <div class="col-span-full flex h-24 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-400">No plate images localized</div>
                                    @endforelse
                                </div>
                            </section>
                        </div>
                    @endif

                    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <h3 class="text-lg font-bold text-slate-900">Incident metadata</h3>
                        <dl class="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
                            @php
                                $metadata = [
                                    ['Violation', str_replace('_', ' ', $violation->violation_type)],
                                    ['Captured', $violation->frame_timestamp?->format('d M Y, H:i:s')],
                                    ['Track ID', '#'.$violation->track_id],
                                    ['Speed', $violation->speed !== null ? number_format($violation->speed, 1).' km/h' : 'Not measured'],
                                    ['Speed limit', $violation->speed_limit !== null ? number_format($violation->speed_limit, 0).' km/h' : 'N/A'],
                                    ['Signal', $violation->signal_state ?: 'N/A'],
                                    ['Direction', $violation->direction ?: 'Unknown'],
                                    ['Vehicle color', ucfirst(strtolower($violation->vehicle_color)).' · '.number_format(($violation->color_confidence ?? 0) * 100, 1).'%'],
                                    ['OCR engine', $violation->ocr_engine ?: 'none'],
                                    ['OCR confidence', number_format(($violation->ocr_confidence ?? 0) * 100, 1).'%'],
                                    ['Raw OCR', $violation->ocr_raw_text ?: 'No text detected'],
                                    ['Database ID', '#'.$violation->id],
                                ];
                            @endphp
                            @foreach ($metadata as [$label, $value])
                                <div>
                                    <dt class="text-xs font-semibold uppercase tracking-wide text-slate-400">{{ $label }}</dt>
                                    <dd class="mt-1 break-words text-sm font-medium text-slate-800">{{ $value }}</dd>
                                </div>
                            @endforeach
                        </dl>
                    </section>
                </div>

                <aside class="space-y-6">
                    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div class="flex items-start justify-between gap-4">
                            <div>
                                <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">Recognized plate</p>
                                <p class="mt-1 text-xl font-bold text-slate-900">{{ $violation->plate_number }}</p>
                                @if ($violation->original_plate_number)
                                    <p class="mt-1 text-xs text-slate-500">Original: {{ $violation->original_plate_number }}</p>
                                @endif
                            </div>
                            <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                                {{ number_format(($violation->ocr_confidence ?? 0) * 100, 1) }}%
                            </span>
                        </div>
                        @if ($violation->plate_crop_path)
                            <a href="{{ asset('storage/'.$violation->plate_crop_path) }}" target="_blank" rel="noopener">
                                <img src="{{ asset('storage/'.$violation->plate_crop_path) }}" alt="Number plate crop"
                                     class="mt-4 max-h-48 w-full rounded-lg bg-slate-100 object-contain ring-1 ring-slate-200">
                            </a>
                        @else
                            <div class="mt-4 flex h-32 items-center justify-center rounded-lg bg-slate-100 text-sm text-slate-400">No plate crop</div>
                        @endif
                    </section>

                    <section class="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                        <h3 class="text-lg font-bold text-slate-900">Officer review</h3>
                        <p class="mt-1 text-sm text-slate-500">Correct the plate if needed, then record a decision.</p>

                        <form method="POST" action="{{ route('violations.update', $violation) }}" class="mt-5 space-y-4">
                            @csrf
                            @method('PATCH')

                            <div>
                                <label for="plate_number" class="block text-sm font-semibold text-slate-700">Plate number</label>
                                <input id="plate_number" name="plate_number" value="{{ old('plate_number', $violation->plate_number) }}" required maxlength="100"
                                       class="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-red-500 focus:ring-red-500">
                                <x-input-error :messages="$errors->get('plate_number')" class="mt-2" />
                            </div>

                            <div>
                                <label for="status" class="block text-sm font-semibold text-slate-700">Decision</label>
                                <select id="status" name="status" class="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-red-500 focus:ring-red-500">
                                    @foreach (['PENDING', 'CONFIRMED', 'DISMISSED'] as $status)
                                        <option value="{{ $status }}" @selected(old('status', $violation->status) === $status)>{{ ucfirst(strtolower($status)) }}</option>
                                    @endforeach
                                </select>
                                <x-input-error :messages="$errors->get('status')" class="mt-2" />
                            </div>

                            <div>
                                <label for="officer_notes" class="block text-sm font-semibold text-slate-700">Officer notes</label>
                                <textarea id="officer_notes" name="officer_notes" rows="4" maxlength="2000" placeholder="Add observations or reasons for the decision…"
                                          class="mt-1 block w-full rounded-lg border-slate-300 shadow-sm focus:border-red-500 focus:ring-red-500">{{ old('officer_notes', $violation->officer_notes) }}</textarea>
                                <x-input-error :messages="$errors->get('officer_notes')" class="mt-2" />
                            </div>

                            <button class="w-full rounded-lg bg-red-700 px-4 py-3 text-sm font-bold text-white shadow-sm hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
                                Save evidence review
                            </button>
                        </form>

                        <div class="mt-6 border-t border-red-100 pt-5">
                            <h4 class="text-sm font-bold text-red-800">Delete violation record</h4>
                            <p class="mt-1 text-xs text-slate-500">This removes the database record. Captured evidence files remain preserved on disk.</p>
                            <form method="POST" action="{{ route('violations.destroy', $violation) }}" class="mt-3"
                                  onsubmit="return confirm('Delete violation {{ $violation->event_id }}? This cannot be undone.');">
                                @csrf
                                @method('DELETE')
                                <button type="submit" class="w-full rounded-lg border border-red-300 bg-white px-4 py-2.5 text-sm font-bold text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2">
                                    Delete record
                                </button>
                            </form>
                        </div>

                        @if ($violation->reviewer)
                            <div class="mt-5 border-t border-slate-200 pt-4 text-xs text-slate-500">
                                Last handled by <strong class="text-slate-700">{{ $violation->reviewer->name }}</strong>
                                @if ($violation->reviewed_at)
                                    on {{ $violation->reviewed_at->format('d M Y, H:i') }}
                                @endif
                            </div>
                        @endif
                    </section>
                </aside>
            </div>
        </div>
    </div>
</x-app-layout>
