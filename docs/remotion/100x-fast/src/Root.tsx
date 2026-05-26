import React from 'react';
import {Composition} from 'remotion';
import {Hermes100xVideo} from './Hermes100xVideo';

export const Root: React.FC = () => (
  <Composition
    id="Hermes100xFast"
    component={Hermes100xVideo}
    durationInFrames={2700}
    fps={30}
    width={1920}
    height={1080}
  />
);
