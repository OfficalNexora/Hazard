/*
 * MOD-EVAC-MS - LED & SENSOR ZONE MAPPING GUIDE
 * 
 * This file explains how to properly configure the physical LED strips
 * and sensors to match the diorama layout.
 * 
 * STEP 1: COUNT YOUR LEDs
 * 
 * If you cut your WS2812B strip into multiple segments:
 * 
 *   SEGMENT 1: 5 LEDs  (Evac Area 1)     → LEDs 0-4
 *   SEGMENT 2: 8 LEDs  (Building 1)      → LEDs 3-10  (Overlaps with Seg 1?)
 *   SEGMENT 3: 4 LEDs  (Evac Area 2)     → LEDs 13-16
 *   SEGMENT 4: 8 LEDs  (Building 2)      → LEDs 13-20 (Overlaps with Seg 3?)
 * 
 *   TOTAL: ~21-22 LEDs
 * 
 * STEP 2: DEFINE YOUR ZONES
 * 
 * Each zone represents a physical area in your diorama.
 * Edit the buildings[] array in MOD_EVAC_MAIN.ino:
 * 
 * Format: {start_led, led_count, fireRed, rainRed, seisRed}
 * 
 *   fireRed = true  → Zone turns RED during fire
 *   fireRed = false → Zone stays GREEN during fire (exit path)
 * 
 * EXAMPLE CONFIGURATION
 * 
 * Physical Layout (Top View):
 * 
 *     ┌───────────────────────────────────────────────┐
 *     │                                               │
 *     │          Building 2                           │
 *     │         (LEDs 21-24?)                         │
 *     │                                               │
 *     │   Floor 1                 EVACUATION AREA 1   │
 *     │   (LEDs 5-7?)            (LEDs 17-20?)        │
 *     │                                               │
 *       __________________________ EVACUTATION AREA 2___|      
 * 
 * Code Configuration:
 */

// CONFIG BASED ON THE USER DIORAMA
#define NUM_LEDS 22  // Set to 22 to cover potential extra power LED

// Format: {"Name", {{start, count, fireRed, rainRed, seisRed}, ...}, numZones}
const Building buildings[] = {
  
  // ============ EVACUATION AREA 1 (EXIT) ============
  // "The first segment on building 2 is the exit for fire"
  {"Evacuation Area 1", {
    {0, 5, true, false, false}  // LEDs 0-4
  }, 1},
  
  // ============ BUILDING 1 ============
  // "This only has a water sensor" - but User config had {false, false, true}
  {"Building 1", {
    {3, 2, false, false, true},  // Floor 1 Left (LEDs 3-4)
    {5, 2, false, false, true},  // Floor 1 Right (LEDs 5-6)
    {7, 2, false, false, true},  // Floor 2 Right (LEDs 7-8)
    {9, 2, false, false, true}   // Floor 2 Left (LEDs 9-10)
  }, 4},
  
  // ============ EVACUATION AREA 2 ============
  {"Evacuation Area 2", {
    {13, 4, false, true, false}  // LEDs 13-16 (Red on Rain)
  }, 1},
  
  // ============ BUILDING 2 ============
  // Fire on RIGHT side (15-16, 17-18), Exit on LEFT side (13-14, 19-20)
  {"Building 2", {
    {13, 2, false, false, true}, // Floor 1 Left (13-14): Green (Exit)
    {15, 2, true, false, true},  // Floor 1 Right (15-16): RED (Fire)
    {17, 2, true, false, true},  // Floor 2 Right (17-18): RED (Fire)
    {19, 2, false, false, true}  // Floor 2 Left (19-20): Green (Exit)
  }, 4}
  
};
