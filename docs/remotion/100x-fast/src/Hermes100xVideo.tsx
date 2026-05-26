import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const metrics = [
  {label: 'Metadata cache', old: 'network probe', value: '0.4211s / 100 lookups', gain: 'cache-first', color: '#33d69f'},
  {label: 'Session writes', old: 'row-by-row flush', value: 'batch transaction', gain: '37.74x', color: '#ffd166'},
  {label: 'Endpoint startup', old: 'HTTP timeout loop', value: 'TCP fast-fail', gain: '9.25x', color: '#4cc9f0'},
  {label: 'Parallel tools', old: 'serial I/O wait', value: 'safe concurrent batch', gain: '5.20x', color: '#b8f7ff'},
  {label: 'Startup discovery', old: 'repeat scans/imports', value: 'fingerprint caches', gain: '2-3x', color: '#8de35a'},
];

const narrationCues = [
  {from: 0, to: 300, text: 'Meet Hermes Agent 100X Fast: measured speed for messages, tasks, delegation, and runtime resources.'},
  {from: 300, to: 690, text: 'Before: repeated metadata probes, row-by-row writes, endpoint timeouts, and serial tool waits.'},
  {from: 690, to: 1050, text: 'After: cache-first metadata, batched SQLite writes, TCP fast-fail, and safe parallel tools.'},
  {from: 1050, to: 1650, text: 'Measured locally: 37.74x faster session writes, 9.25x endpoint startup, and 5.20x parallel tools.'},
  {from: 1650, to: 2190, text: 'Safety stays explicit: old fallbacks, profile-aware cache paths, refresh hooks, and focused regressions.'},
  {from: 2190, to: 2700, text: 'Documented, benchmarked, repeatable: fewer wasted waits, more useful work.'},
];

const sourceImages = {
  hero: staticFile('media/gpt-image-100x-hero-before-after.png'),
  stack: staticFile('media/gpt-image-100x-runtime-stack.png'),
  cover: staticFile('media/gpt-image-100x-video-cover.png'),
  macro: staticFile('media/macro-original-vs-100x-fast.png'),
};

const fade = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, start + 18, end - 18, end], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

const bg = 'linear-gradient(135deg, #071018 0%, #101820 36%, #122632 100%)';

const Backdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = interpolate(Math.sin(frame / 22), [-1, 1], [0.35, 0.9]);
  return (
    <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
      <div
        style={{
          position: 'absolute',
          inset: -160,
          background:
            'radial-gradient(circle at 22% 40%, rgba(77,201,240,.28), transparent 28%), radial-gradient(circle at 78% 48%, rgba(51,214,159,.22), transparent 30%), radial-gradient(circle at 50% 0%, rgba(255,209,102,.16), transparent 24%)',
          opacity: pulse,
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(184,247,255,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(184,247,255,.05) 1px, transparent 1px)',
          backgroundSize: '56px 56px',
          maskImage: 'linear-gradient(to bottom, transparent, black 16%, black 80%, transparent)',
        }}
      />
    </AbsoluteFill>
  );
};

const Title: React.FC<{kicker?: string; title: string; subtitle: string}> = ({kicker, title, subtitle}) => (
  <div style={{position: 'absolute', left: 96, right: 96, top: 76}}>
    {kicker ? (
      <div style={{color: '#8de35a', fontSize: 28, fontWeight: 800, letterSpacing: 0, marginBottom: 12}}>
        {kicker}
      </div>
    ) : null}
    <div style={{color: '#f7fbff', fontSize: 74, lineHeight: 1, fontWeight: 900, letterSpacing: 0}}>
      {title}
    </div>
    <div style={{color: '#c8d9e6', fontSize: 30, marginTop: 18, maxWidth: 1200, lineHeight: 1.28}}>
      {subtitle}
    </div>
  </div>
);

const FramedImage: React.FC<{src: string; left: number; top: number; width: number; opacity?: number}> = ({
  src,
  left,
  top,
  width,
  opacity = 1,
}) => (
  <div
    style={{
      position: 'absolute',
      left,
      top,
      width,
      border: '1px solid rgba(184,247,255,.34)',
      boxShadow: '0 24px 90px rgba(0,0,0,.42)',
      overflow: 'hidden',
      opacity,
    }}
  >
    <Img src={src} style={{width: '100%', display: 'block'}} />
  </div>
);

const MetricCard: React.FC<{metric: (typeof metrics)[number]; index: number; start: number}> = ({metric, index, start}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - start - index * 5, fps, config: {damping: 18, stiffness: 110}});
  const y = 356 + index * 116;
  return (
    <div
      style={{
        position: 'absolute',
        left: 116,
        top: y,
        width: 1688,
        height: 84,
        transform: `translateX(${interpolate(pop, [0, 1], [-90, 0])}px)`,
        opacity: interpolate(pop, [0, 0.4, 1], [0, 1, 1]),
        background: 'rgba(7,16,24,.72)',
        border: `1px solid ${metric.color}`,
        boxShadow: `0 0 34px ${metric.color}30`,
        display: 'grid',
        gridTemplateColumns: '360px 440px 510px 1fr',
        alignItems: 'center',
        padding: '0 28px',
      }}
    >
      <div style={{color: '#f7fbff', fontSize: 30, fontWeight: 850}}>{metric.label}</div>
      <div style={{color: '#ffb4a8', fontSize: 24}}>Before: {metric.old}</div>
      <div style={{color: '#b8f7ff', fontSize: 24}}>After: {metric.value}</div>
      <div style={{color: metric.color, fontSize: 42, fontWeight: 950, textAlign: 'right'}}>{metric.gain}</div>
    </div>
  );
};

const SceneIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 210], [1.08, 1], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <Backdrop />
      <Img
        src={sourceImages.cover}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          opacity: 0.52,
          transform: `scale(${scale})`,
        }}
      />
      <Title
        kicker="Measured hot-path gains"
        title="Hermes Agent 100X Fast"
        subtitle="Before vs after: less repeated work, fewer dead probes, safer parallelism, and cache-first runtime paths."
      />
      <div style={{position: 'absolute', left: 96, bottom: 90, display: 'flex', gap: 18}}>
        {['0.4211s metadata', '37.74x writes', '9.25x startup', '5.20x tools', '2-3x discovery'].map((item) => (
          <div
            key={item}
            style={{
              color: '#f7fbff',
              fontSize: 25,
              fontWeight: 800,
              border: '1px solid rgba(184,247,255,.42)',
              background: 'rgba(7,16,24,.66)',
              padding: '16px 22px',
            }}
          >
            {item}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

const SceneCompare: React.FC = () => {
  const frame = useCurrentFrame();
  const sweep = interpolate(frame, [120, 510], [-260, 1980], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <Backdrop />
      <Title title="The expensive waits were hiding in plain sight" subtitle="Cold metadata probes, local endpoint timeouts, serial writes, and repeated safety parsing were fixed without changing the public tool API." />
      <FramedImage src={sourceImages.hero} left={98} top={260} width={820} />
      <FramedImage src={sourceImages.stack} left={1002} top={260} width={820} />
      <div style={{position: 'absolute', left: sweep, top: 210, width: 16, height: 760, background: '#33d69f', boxShadow: '0 0 70px #33d69f'}} />
      <div style={{position: 'absolute', left: 344, top: 890, color: '#ffb4a8', fontSize: 34, fontWeight: 900}}>BEFORE: repeated waits</div>
      <div style={{position: 'absolute', left: 1250, top: 890, color: '#8de35a', fontSize: 34, fontWeight: 900}}>AFTER: cached, batched, parallel</div>
    </AbsoluteFill>
  );
};

const SceneMetrics: React.FC = () => (
  <AbsoluteFill>
    <Backdrop />
    <Title
      kicker="Measured gains"
      title="Each number owns a concrete hot path"
      subtitle="100X Fast is the optimization track; the table keeps every claim tied to one benchmarked behavior."
    />
    {metrics.map((metric, index) => (
      <MetricCard key={metric.label} metric={metric} index={index} start={190} />
    ))}
  </AbsoluteFill>
);

const SceneArchitecture: React.FC = () => {
  const frame = useCurrentFrame();
  const glow = interpolate(Math.sin(frame / 18), [-1, 1], [0.25, 0.75]);
  const nodes = ['Fingerprint caches', 'Batch writes', 'TCP fast-fail', 'Metadata disk cache', 'Parallel safe tools'];
  return (
    <AbsoluteFill>
      <Backdrop />
      <Title title="How it stays safe" subtitle="The branch keeps old fallback paths, explicit refresh behavior, profile-aware cache paths, and focused regression tests for each optimization group." />
      <div style={{position: 'absolute', left: 164, right: 164, top: 330, height: 430}}>
        {nodes.map((node, index) => {
          const left = index * 330;
          return (
            <React.Fragment key={node}>
              <div
                style={{
                  position: 'absolute',
                  left,
                  top: index % 2 ? 165 : 0,
                  width: 260,
                  height: 160,
                  background: 'rgba(7,16,24,.78)',
                  border: '1px solid rgba(184,247,255,.44)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center',
                  color: '#f7fbff',
                  fontSize: 30,
                  fontWeight: 850,
                  padding: 24,
                  boxShadow: `0 0 ${40 * glow}px rgba(51,214,159,.42)`,
                }}
              >
                {node}
              </div>
              {index < nodes.length - 1 ? (
                <div
                  style={{
                    position: 'absolute',
                    left: left + 258,
                    top: index % 2 ? 232 : 68,
                    width: 104,
                    height: 4,
                    background: '#33d69f',
                    boxShadow: '0 0 24px #33d69f',
                  }}
                />
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
      <FramedImage src={sourceImages.macro} left={1240} top={690} width={520} opacity={0.82} />
    </AbsoluteFill>
  );
};

const SceneClose: React.FC = () => (
  <AbsoluteFill>
    <Backdrop />
    <Title
      kicker="Ready for the next Hermes release"
      title="Documented, benchmarked, and repeatable"
      subtitle="A reapply playbook maps every optimization to files, commits, tests, benchmarks, and visual refresh steps."
    />
    <div style={{position: 'absolute', left: 140, top: 410, width: 1640, color: '#f7fbff', fontSize: 46, lineHeight: 1.42, fontWeight: 780}}>
      Reuse the playbook. Port one optimization at a time. Run focused regressions. Update the visuals only after the measurements are real.
    </div>
    <div style={{position: 'absolute', left: 140, bottom: 118, color: '#33d69f', fontSize: 64, fontWeight: 950}}>
      Hermes Agent 100X Fast
    </div>
  </AbsoluteFill>
);

const NarrationOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const cue = narrationCues.find((item) => frame >= item.from && frame < item.to) ?? narrationCues[narrationCues.length - 1];
  const progress = interpolate(frame, [0, 2700], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const cueOpacity = interpolate(frame, [cue.from, cue.from + 18, cue.to - 18, cue.to], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: 9,
          background: 'rgba(184,247,255,.18)',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #33d69f, #ffd166, #4cc9f0)',
            boxShadow: '0 0 28px rgba(51,214,159,.72)',
          }}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          left: 96,
          right: 96,
          bottom: 34,
          opacity: cueOpacity,
          color: '#f7fbff',
          fontSize: 30,
          lineHeight: 1.28,
          fontWeight: 780,
          textAlign: 'center',
          padding: '20px 34px',
          background: 'rgba(7,16,24,.76)',
          border: '1px solid rgba(184,247,255,.34)',
          boxShadow: '0 18px 60px rgba(0,0,0,.38)',
        }}
      >
        {cue.text}
      </div>
      <div
        style={{
          position: 'absolute',
          right: 86,
          top: 42,
          color: '#b8f7ff',
          fontSize: 22,
          fontWeight: 850,
          padding: '12px 18px',
          background: 'rgba(7,16,24,.62)',
          border: '1px solid rgba(184,247,255,.26)',
        }}
      >
        narrated launch cut
      </div>
    </AbsoluteFill>
  );
};

export const Hermes100xVideo: React.FC = () => (
  <VideoTimeline />
);

const VideoTimeline: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{fontFamily: 'Inter, Segoe UI, Arial, sans-serif'}}>
      <Audio src={staticFile('sound/hermes-100x-fast-soundtrack.wav')} volume={0.24} />
      <Audio src={staticFile('sound/hermes-100x-fast-voiceover.wav')} volume={1} />
      <Sequence from={0} durationInFrames={540}>
        <div style={{opacity: fade(frame, 0, 540)}}><SceneIntro /></div>
      </Sequence>
      <Sequence from={480} durationInFrames={630}>
        <div style={{opacity: fade(frame, 480, 1110)}}><SceneCompare /></div>
      </Sequence>
      <Sequence from={1050} durationInFrames={660}>
        <div style={{opacity: fade(frame, 1050, 1710)}}><SceneMetrics /></div>
      </Sequence>
      <Sequence from={1650} durationInFrames={600}>
        <div style={{opacity: fade(frame, 1650, 2250)}}><SceneArchitecture /></div>
      </Sequence>
      <Sequence from={2190} durationInFrames={510}>
        <div style={{opacity: fade(frame, 2190, 2700)}}><SceneClose /></div>
      </Sequence>
      <NarrationOverlay />
    </AbsoluteFill>
  );
};
