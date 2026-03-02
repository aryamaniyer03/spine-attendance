import { useCurrentFrame, useVideoConfig, interpolate, Easing } from "remotion";

export const LoadingSpinner = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Continuous rotation: full 360° every 1.2 seconds
  const rotationDuration = 1.2 * fps;
  const rotation = interpolate(
    frame % rotationDuration,
    [0, rotationDuration],
    [0, 360]
  );

  // Pulsing arc length using easing for smooth feel
  const pulseDuration = 1.5 * fps;
  const pulseProgress = (frame % pulseDuration) / pulseDuration;
  const dashLength = interpolate(
    Math.sin(pulseProgress * Math.PI * 2),
    [-1, 1],
    [40, 220]
  );

  const size = 120;
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference - (dashLength / 360) * circumference;

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: "#000000",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <svg
        width={size}
        height={size}
        style={{
          transform: `rotate(${rotation}deg)`,
        }}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#333333"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#ffffff"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
        />
      </svg>
    </div>
  );
};
