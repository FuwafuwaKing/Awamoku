using RosMessageTypes.Std;
using Unity.Robotics.ROSTCPConnector;
using UnityEngine;

namespace Awamoku
{
    public sealed class CloudStateView : MonoBehaviour
    {
        [SerializeField] Renderer targetRenderer;
        [SerializeField] Light glowLight;
        [SerializeField] float bobAmplitude = 0.08f;
        [SerializeField] float bobSpeed = 1.5f;

        float baseHeight;
        string cloudState = "DRIFT";
        string effectMode = "NORMAL";

        void Awake()
        {
            if (targetRenderer == null)
            {
                targetRenderer = GetComponentInChildren<Renderer>();
            }
            baseHeight = transform.position.y;
        }

        void Start()
        {
            var ros = ROSConnection.GetOrCreateInstance();
            ros.Subscribe<StringMsg>("/awamoku/cloud/state", msg => cloudState = msg.data);
            ros.Subscribe<StringMsg>("/awamoku/effect/mode", msg => effectMode = msg.data);
        }

        void Update()
        {
            var position = transform.position;
            position.y = baseHeight + Mathf.Sin(Time.time * bobSpeed) * bobAmplitude;
            transform.position = position;
            var color = ColorForState(cloudState, effectMode);
            if (targetRenderer != null)
            {
                targetRenderer.material.color = color;
            }
            if (glowLight != null)
            {
                glowLight.color = color;
                glowLight.intensity = effectMode == "COMFORT" ? 2.4f : 1.2f;
            }
        }

        static Color ColorForState(string state, string mode)
        {
            if (mode == "PANIC" || state == "PANIC_RETURN")
            {
                return new Color(1f, 0.38f, 0.28f);
            }
            if (mode == "COMFORT" || state.StartsWith("COMFORT"))
            {
                return new Color(0.65f, 1f, 0.82f);
            }
            if (mode == "SHY" || state.StartsWith("SHY"))
            {
                return new Color(1f, 0.62f, 0.68f);
            }
            if (state.Contains("RED"))
            {
                return new Color(1f, 0.72f, 0.72f);
            }
            if (state.Contains("WHITE"))
            {
                return new Color(0.72f, 0.9f, 1f);
            }
            if (mode == "COOLDOWN" || state == "COOLDOWN")
            {
                return new Color(0.72f, 0.85f, 1f);
            }
            return Color.white;
        }
    }
}
