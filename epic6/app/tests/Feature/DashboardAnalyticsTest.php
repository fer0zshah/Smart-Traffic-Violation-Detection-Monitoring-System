<?php

namespace Tests\Feature;

use App\Models\User;
use App\Models\Violation;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class DashboardAnalyticsTest extends TestCase
{
    use RefreshDatabase;

    private function officer(): User
    {
        return User::factory()->create(['role' => 'officer']);
    }

    public function test_guest_cannot_open_dashboard(): void
    {
        $this->get('/dashboard')->assertRedirect('/login');
    }

    public function test_officer_sees_dashboard_analytics(): void
    {
        Violation::factory()->create([
            'plate_number' => 'DHAKA-GA-1234',
            'violation_type' => 'RED_LIGHT',
            'status' => 'PENDING',
            'vehicle_color' => 'RED',
            'frame_timestamp' => now(),
            'ocr_confidence' => 0.91,
        ]);

        Violation::factory()->create([
            'plate_number' => 'DHAKA-GA-1234',
            'violation_type' => 'OVERSPEED',
            'status' => 'CONFIRMED',
            'vehicle_color' => 'WHITE',
            'frame_timestamp' => now()->subDay(),
            'ocr_confidence' => 0.88,
        ]);

        Violation::factory()->create([
            'plate_number' => 'UNREADABLE',
            'violation_type' => 'RED_LIGHT',
            'status' => 'DISMISSED',
            'vehicle_color' => 'BLACK',
            'frame_timestamp' => now()->subDays(2),
            'ocr_confidence' => 0.35,
        ]);

        $this->actingAs($this->officer())
            ->get('/dashboard')
            ->assertOk()
            ->assertSee('Traffic violation dashboard')
            ->assertSee('Total evidence')
            ->assertSee('Pending review')
            ->assertSee('OCR attention')
            ->assertSee('RED LIGHT')
            ->assertSee('OVERSPEED')
            ->assertSee('DHAKA-GA-1234')
            ->assertSee('Latest evidence');
    }
}
