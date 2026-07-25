using Awamoku;
using UnityEditor;
using UnityEditor.Events;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.InputSystem.UI;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace AwamokuEditor
{
    public static class AwamokuPrototypeSceneBuilder
    {
        [MenuItem("Awamoku/Create Prototype Scene")]
        public static void CreatePrototypeScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            scene.name = "AwamokuPrototype";

            AddRosConnection();
            var cloud = CreateCloud();
            var dashboard = CreateDashboard(cloud.transform);
            cloud.AddComponent<CloudStateView>();
            cloud.AddComponent<CloudEffectPlayer>();

            var camera = new GameObject("Main Camera").AddComponent<Camera>();
            camera.tag = "MainCamera";
            camera.transform.position = new Vector3(0f, 8f, -0.1f);
            camera.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
            camera.orthographic = true;
            camera.orthographicSize = 4.2f;
            camera.backgroundColor = new Color(0.45f, 0.55f, 0.62f);

            var light = new GameObject("Directional Light").AddComponent<Light>();
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            CreateFieldMarkers();
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/AwamokuPrototype.unity");
            Selection.activeGameObject = dashboard.gameObject;
        }

        static void AddRosConnection()
        {
            var prefab = Resources.Load<GameObject>("ROSConnectionPrefab");
            if (prefab != null)
            {
                PrefabUtility.InstantiatePrefab(prefab);
            }
        }

        static GameObject CreateCloud()
        {
            var root = new GameObject("AwamokuCloud");
            root.transform.position = new Vector3(0f, 0.35f, 0f);
            var body = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            body.name = "CloudBody";
            body.transform.SetParent(root.transform, false);
            body.transform.localScale = new Vector3(0.8f, 0.45f, 0.6f);
            var renderer = body.GetComponent<Renderer>();
            renderer.sharedMaterial = ColoredMaterial("AwamokuCloudMaterial", Color.white);
            var glow = new GameObject("CloudGlow").AddComponent<Light>();
            glow.transform.SetParent(root.transform, false);
            glow.type = LightType.Point;
            glow.range = 2.5f;
            glow.intensity = 1.2f;
            return root;
        }

        static AwamokuDashboard CreateDashboard(Transform cloudTransform)
        {
            if (Object.FindAnyObjectByType<EventSystem>() == null)
            {
                new GameObject("EventSystem", typeof(EventSystem), typeof(InputSystemUIInputModule));
            }

            var canvas = new GameObject("AwamokuCanvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvasComponent = canvas.GetComponent<Canvas>();
            canvasComponent.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvas.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280f, 720f);

            var panel = new GameObject("ControlPanel", typeof(Image));
            panel.transform.SetParent(canvas.transform, false);
            var panelRect = panel.GetComponent<RectTransform>();
            panelRect.anchorMin = new Vector2(0f, 0f);
            panelRect.anchorMax = new Vector2(0f, 1f);
            panelRect.sizeDelta = new Vector2(320f, 0f);
            panelRect.anchoredPosition = new Vector2(160f, 0f);
            panel.GetComponent<Image>().color = new Color(0.08f, 0.1f, 0.12f, 0.86f);

            var redSlider = CreateSlider(panel.transform, "Red Voice", new Vector2(0f, 270f));
            var whiteSlider = CreateSlider(panel.transform, "White Voice", new Vector2(0f, 200f));
            var gameText = CreateText(panel.transform, "Game: IDLE", new Vector2(0f, 125f));
            var cloudText = CreateText(panel.transform, "Cloud: DRIFT", new Vector2(0f, 95f));
            var targetText = CreateText(panel.transform, "Target: NONE", new Vector2(0f, 65f));
            var redScore = CreateText(panel.transform, "Red Score: 0", new Vector2(0f, 30f));
            var whiteScore = CreateText(panel.transform, "White Score: 0", new Vector2(0f, 0f));
            var redComfort = CreateText(panel.transform, "Red Comfort: 0.00", new Vector2(0f, -35f));
            var whiteComfort = CreateText(panel.transform, "White Comfort: 0.00", new Vector2(0f, -65f));
            var timer = CreateText(panel.transform, "Time: 75.0", new Vector2(0f, -100f));
            var effect = CreateText(panel.transform, "Effect: NORMAL", new Vector2(0f, -130f));
            var rosPose = CreateText(panel.transform, "ROS Pose: waiting /odom", new Vector2(0f, -165f));
            var unityPose = CreateText(panel.transform, "Unity Cloud: x=0.00 z=0.00", new Vector2(0f, -195f));
            var desired = CreateText(panel.transform, "Desired: waiting", new Vector2(0f, -225f));
            var cmdVel = CreateText(panel.transform, "CmdVel: waiting", new Vector2(0f, -255f));

            var dashboardObject = new GameObject("AwamokuDashboard");
            var dashboard = dashboardObject.AddComponent<AwamokuDashboard>();
            dashboard.Configure(
                redSlider,
                whiteSlider,
                gameText,
                cloudText,
                targetText,
                redScore,
                whiteScore,
                redComfort,
                whiteComfort,
                timer,
                effect,
                rosPose,
                unityPose,
                desired,
                cmdVel,
                cloudTransform);

            CreateButton(panel.transform, "Start", new Vector2(-78f, -295f), dashboard.SendStart);
            CreateButton(panel.transform, "Reset", new Vector2(78f, -295f), dashboard.SendReset);
            CreateButton(panel.transform, "Stop", new Vector2(-78f, -337f), dashboard.SendStop);
            CreateButton(panel.transform, "Estop", new Vector2(78f, -337f), dashboard.SendEstop);
            return dashboard;
        }

        static Slider CreateSlider(Transform parent, string label, Vector2 position)
        {
            CreateText(parent, label, position + new Vector2(0f, 25f));
            var obj = DefaultControls.CreateSlider(DefaultUiResources());
            obj.name = label + " Slider";
            obj.transform.SetParent(parent, false);
            var rect = obj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(250f, 24f);
            rect.anchoredPosition = position;
            var slider = obj.GetComponent<Slider>();
            slider.minValue = 0f;
            slider.maxValue = 1f;
            return slider;
        }

        static Button CreateButton(Transform parent, string label, Vector2 position, UnityEngine.Events.UnityAction action)
        {
            var obj = DefaultControls.CreateButton(DefaultUiResources());
            obj.name = label;
            obj.transform.SetParent(parent, false);
            var rect = obj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(120f, 36f);
            rect.anchoredPosition = position;
            obj.GetComponent<Image>().color = new Color(0.18f, 0.22f, 0.27f, 1f);
            var button = obj.GetComponent<Button>();
            UnityEventTools.AddPersistentListener(button.onClick, action);
            var text = obj.GetComponentInChildren<Text>();
            if (text != null)
            {
                text.text = label;
                text.color = Color.white;
                text.alignment = TextAnchor.MiddleCenter;
            }
            return button;
        }

        static Text CreateText(Transform parent, string value, Vector2 position)
        {
            var obj = new GameObject(value, typeof(Text));
            obj.transform.SetParent(parent, false);
            var rect = obj.GetComponent<RectTransform>();
            rect.sizeDelta = new Vector2(280f, 24f);
            rect.anchoredPosition = position;
            var text = obj.GetComponent<Text>();
            text.text = value;
            text.font = BuiltinFont();
            text.fontSize = 16;
            text.color = Color.white;
            return text;
        }

        static DefaultControls.Resources DefaultUiResources()
        {
            return new DefaultControls.Resources
            {
                standard = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/UISprite.psd"),
                background = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/Background.psd"),
                inputField = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/InputFieldBackground.psd"),
                knob = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/Knob.psd"),
                checkmark = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/Checkmark.psd"),
                dropdown = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/DropdownArrow.psd"),
                mask = AssetDatabase.GetBuiltinExtraResource<Sprite>("UI/Skin/UIMask.psd"),
            };
        }

        static Font BuiltinFont()
        {
            return Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf")
                ?? Resources.GetBuiltinResource<Font>("Arial.ttf");
        }

        static void CreateFieldMarkers()
        {
            CreateMarker("Center", Vector3.zero, Color.green, 0.15f);
            CreateMarker("RedTeam", new Vector3(0f, 0.02f, 2.5f), Color.red, 0.2f);
            CreateMarker("WhiteTeam", new Vector3(0f, 0.02f, -2.5f), Color.cyan, 0.2f);
        }

        static void CreateMarker(string name, Vector3 position, Color color, float scale)
        {
            var obj = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            obj.name = name;
            obj.transform.position = position;
            obj.transform.localScale = new Vector3(scale, 0.02f, scale);
            obj.GetComponent<Renderer>().sharedMaterial = ColoredMaterial(name + "Material", color);
        }

        static Material ColoredMaterial(string name, Color color)
        {
            var shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("Standard");
            return new Material(shader)
            {
                name = name,
                color = color
            };
        }
    }
}
