import { Composition } from "remotion";
import { LoadingSpinner } from "./LoadingSpinner";

export const RemotionRoot = () => {
  return (
    <Composition
      id="LoadingSpinner"
      component={LoadingSpinner}
      durationInFrames={90}
      fps={30}
      width={320}
      height={240}
    />
  );
};
