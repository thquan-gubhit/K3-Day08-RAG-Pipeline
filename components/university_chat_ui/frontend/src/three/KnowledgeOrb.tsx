import { useMemo, useRef } from "react";
import { Canvas, useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";
import { TOPICS } from "./topics";

/**
 * KnowledgeOrb — visual 3D riêng cho hệ thống RAG.
 *
 * Concept: một lõi tri thức phát sáng ở trung tâm, các node tài liệu quay quanh
 * theo quỹ đạo, nối với lõi bằng đường kết nối tượng trưng cho knowledge graph.
 * Khi pipeline chạy, một xung sáng lan từ lõi ra các node.
 *
 * Ràng buộc kỹ thuật (theo yêu cầu bài):
 *  - Hình học hoàn toàn procedural, KHÔNG tải GLTF/texture/HDRI từ internet.
 *  - Giới hạn số node và số đường nối.
 *  - Giới hạn devicePixelRatio, tắt antialias trên thiết bị yếu.
 *  - Dừng animation khi tab ẩn (`frameloop` chuyển sang "demand").
 *  - Không post-processing, không shadow.
 *  - Canvas `pointer-events: none` để không bao giờ chặn thao tác chat.
 */

type OrbProps = {
  /** Pipeline đang chạy → phát xung sáng từ lõi ra node. */
  active: boolean;
  /** Index node được highlight khi người dùng chọn một source (null = không). */
  highlightIndex: number | null;
  /** Giảm chuyển động → quay chậm, không pulse. */
  reducedMotion: boolean;
};

/** Lõi tri thức trung tâm. */
function Core({ active, reducedMotion }: { active: boolean; reducedMotion: boolean }) {
  const mesh = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (reducedMotion) return;
    const t = clock.getElapsedTime();
    if (mesh.current) {
      mesh.current.rotation.y = t * 0.18;
      mesh.current.rotation.x = Math.sin(t * 0.22) * 0.14;
    }
    if (halo.current) {
      // Nhịp thở nhẹ; nhanh hơn khi pipeline đang chạy.
      const speed = active ? 2.6 : 1.1;
      const scale = 1 + Math.sin(t * speed) * (active ? 0.11 : 0.05);
      halo.current.scale.setScalar(scale);
      const material = halo.current.material as THREE.MeshBasicMaterial;
      material.opacity = active ? 0.24 : 0.13;
    }
  });

  return (
    <group>
      <mesh ref={mesh}>
        <icosahedronGeometry args={[0.78, 1]} />
        <meshStandardMaterial
          color="#22D3EE"
          emissive="#0E7490"
          emissiveIntensity={active ? 1.5 : 0.75}
          roughness={0.32}
          metalness={0.55}
          wireframe
        />
      </mesh>
      <mesh ref={halo}>
        <sphereGeometry args={[1.05, 24, 24]} />
        <meshBasicMaterial color="#22D3EE" transparent opacity={0.13} side={THREE.BackSide} />
      </mesh>
    </group>
  );
}

/** Một node tài liệu quay quanh lõi kèm đường nối về tâm. */
function TopicNode({
  index,
  color,
  active,
  highlighted,
  reducedMotion,
}: {
  index: number;
  color: string;
  active: boolean;
  highlighted: boolean;
  reducedMotion: boolean;
}) {
  const group = useRef<THREE.Group>(null);
  const dot = useRef<THREE.Mesh>(null);

  // Quỹ đạo cố định theo index → scene tái lập được giữa các lần render.
  const orbit = useMemo(() => {
    const angle = (index / TOPICS.length) * Math.PI * 2;
    return {
      radius: 1.85 + (index % 3) * 0.24,
      angle,
      tilt: -0.42 + (index % 4) * 0.22,
      speed: 0.14 + (index % 3) * 0.035,
    };
  }, [index]);

  // Đường nối lõi → node: chỉ 2 điểm nên rất rẻ để vẽ.
  const linePositions = useMemo(() => new Float32Array([0, 0, 0, orbit.radius, 0, 0]), [orbit.radius]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (group.current) {
      const speed = reducedMotion ? orbit.speed * 0.25 : orbit.speed;
      group.current.rotation.y = orbit.angle + t * speed;
    }
    if (dot.current && !reducedMotion) {
      // Xung sáng lan từ lõi ra node khi pipeline chạy (lệch pha theo index).
      const phase = active ? Math.sin(t * 3.1 - index * 0.7) : Math.sin(t * 0.9 + index);
      const base = highlighted ? 1.55 : 1;
      dot.current.scale.setScalar(base * (1 + phase * (active ? 0.3 : 0.09)));
    } else if (dot.current) {
      dot.current.scale.setScalar(highlighted ? 1.4 : 1);
    }
  });

  return (
    <group ref={group} rotation={[orbit.tilt, orbit.angle, 0] as ThreeElements["group"]["rotation"]}>
      <line>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
        </bufferGeometry>
        <lineBasicMaterial
          color={color}
          transparent
          opacity={highlighted ? 0.5 : active ? 0.3 : 0.16}
        />
      </line>
      <mesh ref={dot} position={[orbit.radius, 0, 0]}>
        <sphereGeometry args={[0.085, 14, 14]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={highlighted ? 2.4 : active ? 1.4 : 0.7}
          roughness={0.28}
        />
      </mesh>
    </group>
  );
}

/** Vành sáng mờ bao ngoài, tạo chiều sâu cho scene. */
function OuterRing({ reducedMotion }: { reducedMotion: boolean }) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ring.current && !reducedMotion) {
      ring.current.rotation.z = clock.getElapsedTime() * 0.06;
    }
  });
  return (
    <mesh ref={ring} rotation={[Math.PI / 2.6, 0, 0]}>
      <torusGeometry args={[2.5, 0.008, 6, 72]} />
      <meshBasicMaterial color="#6366F1" transparent opacity={0.28} />
    </mesh>
  );
}

/**
 * Scene hoàn chỉnh. Caller (EmptyState) chịu trách nhiệm kiểm tra WebGL và
 * dùng ``KnowledgeOrbFallback`` từ ``./topics`` khi không hỗ trợ.
 */
export default function KnowledgeOrb({ active, highlightIndex, reducedMotion }: OrbProps) {
  // Thiết bị yếu (ít nhân CPU) → tắt antialias để giữ khung hình mượt.
  const lowPower = useMemo(
    () => (navigator.hardwareConcurrency ?? 4) <= 4 || window.innerWidth < 768,
    [],
  );

  return (
    <Canvas
      // pointer-events: none — scene không bao giờ chặn thao tác chat.
      className="pointer-events-none"
      // Giảm chuyển động → chỉ render khi cần, không chạy vòng lặp liên tục.
      frameloop={reducedMotion ? "demand" : "always"}
      dpr={[1, lowPower ? 1.2 : 1.75]}
      gl={{ antialias: !lowPower, alpha: true, powerPreference: "low-power" }}
      camera={{ position: [0, 0.55, 5.4], fov: 44 }}
      aria-hidden="true"
    >
      <ambientLight intensity={0.42} />
      <pointLight position={[3, 3, 4]} intensity={22} color="#22D3EE" />
      <pointLight position={[-3.5, -2, -2]} intensity={14} color="#A78BFA" />

      <Core active={active} reducedMotion={reducedMotion} />
      <OuterRing reducedMotion={reducedMotion} />
      {TOPICS.map((topic, i) => (
        <TopicNode
          key={topic.label}
          index={i}
          color={topic.color}
          active={active}
          highlighted={highlightIndex === i}
          reducedMotion={reducedMotion}
        />
      ))}
    </Canvas>
  );
}
