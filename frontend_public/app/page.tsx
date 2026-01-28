'use client';

import { usePublicAuth } from '@/lib/hooks';
import PairingScreen from '@/components/layout/PairingScreen';
import PublicDashboard from '@/components/layout/PublicDashboard';

export default function PublicPortal() {
  // I implemented this switch logic to enforce a strict pairing requirement.
  // This ensures that the public display cannot be accessed without physical proximity (access code verification) to the station.
  const { isPaired, pair, unpair } = usePublicAuth();

  if (!isPaired) {
    return <PairingScreen onPair={pair} />;
  }

  return <PublicDashboard onUnpair={unpair} />;
}
