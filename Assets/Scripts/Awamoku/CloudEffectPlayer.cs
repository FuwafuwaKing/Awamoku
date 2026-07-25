using System.Collections.Generic;
using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;
using UnityEngine.Rendering;

namespace Awamoku
{
    public sealed class CloudEffectPlayer : MonoBehaviour
    {
        [SerializeField] ParticleSystem bubbleParticles;
        [SerializeField] AudioSource audioSource;
        [SerializeField] float redTeamZ = 2.5f;
        [SerializeField] float whiteTeamZ = -2.5f;
        [SerializeField] int rewardBubbleCount = 28;
        [SerializeField] int panicBubbleCount = 18;
        [SerializeField] float bubbleLifetime = 1.8f;
        [SerializeField] float bubbleSpeed = 2.3f;
        [SerializeField] float bubbleSpread = 0.32f;
        [SerializeField] float bubbleStartSize = 0.16f;
        [SerializeField] float bubbleEndSize = 0.34f;

        string cloudState = "DRIFT";
        string targetTeam = "NONE";
        Material bubbleMaterial;
        readonly List<BubbleVisual> activeBubbles = new List<BubbleVisual>();

        sealed class BubbleVisual
        {
            public Transform Transform;
            public Renderer Renderer;
            public Vector3 Velocity;
            public float Age;
            public float Lifetime;
            public float StartSize;
            public float EndSize;
        }

        void Start()
        {
            EnsureBubbleParticles();
            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<StringMsg>("/awamoku/effect/event", OnEvent);
            ros.Subscribe<StringMsg>("/awamoku/cloud/state", msg => cloudState = msg.data);
            ros.Subscribe<StringMsg>("/awamoku/cloud/target_team", msg => targetTeam = msg.data);
        }

        void Update()
        {
            for (var i = activeBubbles.Count - 1; i >= 0; i--)
            {
                var bubble = activeBubbles[i];
                bubble.Age += Time.deltaTime;
                if (bubble.Age >= bubble.Lifetime || bubble.Transform == null)
                {
                    if (bubble.Transform != null)
                    {
                        Destroy(bubble.Transform.gameObject);
                    }
                    activeBubbles.RemoveAt(i);
                    continue;
                }

                var t = bubble.Age / bubble.Lifetime;
                bubble.Transform.position += bubble.Velocity * Time.deltaTime;
                bubble.Transform.localScale = Vector3.one * Mathf.Lerp(bubble.StartSize, bubble.EndSize, t);
                if (bubble.Renderer != null)
                {
                    bubble.Renderer.material.color = Color.Lerp(
                        new Color(0.70f, 0.95f, 1f, 0.95f),
                        new Color(1f, 1f, 1f, 0.30f),
                        t);
                }
            }
        }

        void OnEvent(StringMsg msg)
        {
            if (msg.data == "NONE")
            {
                return;
            }
            if ((msg.data == "BUBBLE_PANIC" || msg.data == "BUBBLE_REWARD") && bubbleParticles != null)
            {
                var direction = AimBubblesAtSettledTeam();
                bubbleParticles.Emit(msg.data == "BUBBLE_REWARD" ? 55 : 35);
                SpawnVisibleBubbles(direction, msg.data == "BUBBLE_REWARD" ? rewardBubbleCount : panicBubbleCount);
            }
            if (audioSource != null)
            {
                audioSource.Play();
            }
            Debug.Log($"Awamoku effect event: {msg.data}");
        }

        void EnsureBubbleParticles()
        {
            if (bubbleParticles != null)
            {
                return;
            }

            var obj = new GameObject("DirectionalBubbles");
            obj.transform.SetParent(transform, false);
            obj.transform.localPosition = new Vector3(0f, 0.05f, 0f);
            bubbleParticles = obj.AddComponent<ParticleSystem>();

            var main = bubbleParticles.main;
            main.loop = false;
            main.playOnAwake = false;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.0f, 1.8f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.2f, 2.2f);
            main.startSize = new ParticleSystem.MinMaxCurve(0.08f, 0.18f);
            main.startColor = new ParticleSystem.MinMaxGradient(
                new Color(0.75f, 0.95f, 1f, 0.78f),
                new Color(1f, 1f, 1f, 0.55f));

            var emission = bubbleParticles.emission;
            emission.enabled = false;

            var shape = bubbleParticles.shape;
            shape.enabled = true;
            shape.shapeType = ParticleSystemShapeType.Cone;
            shape.angle = 13f;
            shape.radius = 0.12f;
            shape.length = 0.25f;

            var velocity = bubbleParticles.velocityOverLifetime;
            velocity.enabled = true;
            velocity.space = ParticleSystemSimulationSpace.Local;
            velocity.y = new ParticleSystem.MinMaxCurve(0.15f, 0.45f);

            var colorOverLifetime = bubbleParticles.colorOverLifetime;
            colorOverLifetime.enabled = true;
            var gradient = new Gradient();
            gradient.SetKeys(
                new[]
                {
                    new GradientColorKey(new Color(0.75f, 0.95f, 1f), 0f),
                    new GradientColorKey(Color.white, 1f),
                },
                new[]
                {
                    new GradientAlphaKey(0.85f, 0f),
                    new GradientAlphaKey(0f, 1f),
                });
            colorOverLifetime.color = gradient;

            var renderer = bubbleParticles.GetComponent<ParticleSystemRenderer>();
            renderer.renderMode = ParticleSystemRenderMode.Billboard;
            renderer.sortingOrder = 20;
            renderer.shadowCastingMode = ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            renderer.material = BubbleMaterial();
        }

        Vector3 AimBubblesAtSettledTeam()
        {
            var settledTeam = SettledTeam();
            var targetZ = settledTeam == "RED" ? redTeamZ : whiteTeamZ;
            var target = new Vector3(0f, transform.position.y, targetZ);
            var direction = target - transform.position;
            direction.y = 0f;
            if (direction.sqrMagnitude < 0.001f)
            {
                direction = settledTeam == "RED" ? Vector3.forward : Vector3.back;
            }
            direction.Normalize();
            bubbleParticles.transform.rotation = Quaternion.LookRotation(direction, Vector3.up);
            return direction;
        }

        void SpawnVisibleBubbles(Vector3 direction, int count)
        {
            var origin = transform.position + Vector3.up * 0.35f + direction * 0.35f;
            for (var i = 0; i < count; i++)
            {
                var obj = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                obj.name = "AwamokuBubble";
                obj.transform.position = origin
                    + Vector3.right * Random.Range(-0.18f, 0.18f)
                    + Vector3.up * Random.Range(-0.08f, 0.18f);
                var size = Random.Range(bubbleStartSize * 0.75f, bubbleStartSize * 1.35f);
                obj.transform.localScale = Vector3.one * size;

                var collider = obj.GetComponent<Collider>();
                if (collider != null)
                {
                    Destroy(collider);
                }

                var renderer = obj.GetComponent<Renderer>();
                renderer.material = new Material(BubbleMaterial());
                renderer.material.color = new Color(0.70f, 0.95f, 1f, 0.95f);

                var side = Vector3.right * Random.Range(-bubbleSpread, bubbleSpread);
                var lift = Vector3.up * Random.Range(0.12f, 0.55f);
                var velocity = (direction * Random.Range(0.85f, 1.25f) + side + lift).normalized
                    * Random.Range(bubbleSpeed * 0.75f, bubbleSpeed * 1.25f);

                activeBubbles.Add(new BubbleVisual
                {
                    Transform = obj.transform,
                    Renderer = renderer,
                    Velocity = velocity,
                    Age = 0f,
                    Lifetime = Random.Range(bubbleLifetime * 0.75f, bubbleLifetime * 1.25f),
                    StartSize = size,
                    EndSize = Random.Range(bubbleEndSize * 0.75f, bubbleEndSize * 1.25f),
                });
            }
        }

        Material BubbleMaterial()
        {
            if (bubbleMaterial != null)
            {
                return bubbleMaterial;
            }

            var shader = Shader.Find("Universal Render Pipeline/Unlit")
                ?? Shader.Find("Universal Render Pipeline/Lit")
                ?? Shader.Find("Standard");
            bubbleMaterial = new Material(shader)
            {
                name = "AwamokuVisibleBubbleMaterial",
                color = new Color(0.70f, 0.95f, 1f, 0.95f)
            };
            bubbleMaterial.SetFloat("_Surface", 1f);
            bubbleMaterial.SetFloat("_Blend", 0f);
            bubbleMaterial.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
            bubbleMaterial.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
            bubbleMaterial.SetInt("_ZWrite", 0);
            bubbleMaterial.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            bubbleMaterial.renderQueue = (int)RenderQueue.Transparent;
            return bubbleMaterial;
        }

        string SettledTeam()
        {
            if (cloudState.EndsWith("RED") || targetTeam == "RED")
            {
                return "RED";
            }
            if (cloudState.EndsWith("WHITE") || targetTeam == "WHITE")
            {
                return "WHITE";
            }
            return transform.position.z >= 0f ? "RED" : "WHITE";
        }
    }
}
