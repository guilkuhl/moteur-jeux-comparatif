using Godot;

public partial class Main : Node2D
{
    private const int WindowW = 960;
    private const int WindowH = 540;
    private const int SpawnPerSecond = 10;
    private const float MinFps = 20f;
    private const float BallRadius = 8f;

    private ImageTexture _ballTexture;
    private float _spawnTimer;
    private readonly float _spawnInterval = 1f / SpawnPerSecond;
    private int _activeCount;
    private bool _stopped;

    private Label _fpsLabel;
    private Label _countLabel;

    public override void _Ready()
    {
        _fpsLabel = GetNode<Label>("UI/VBox/FPSLabel");
        _countLabel = GetNode<Label>("UI/VBox/CountLabel");
        GenerateBallTexture();
        CreateWalls();
    }

    private void GenerateBallTexture()
    {
        var img = Image.Create(16, 16, false, Image.Format.Rgba8);
        var center = new Vector2(8f, 8f);
        for (int x = 0; x < 16; x++)
        for (int y = 0; y < 16; y++)
        {
            float dist = new Vector2(x + 0.5f, y + 0.5f).DistanceTo(center);
            img.SetPixel(x, y, dist <= 7.5f ? new Color(0.3f, 0.7f, 1f) : Colors.Transparent);
        }
        _ballTexture = ImageTexture.CreateFromImage(img);
    }

    private void CreateWalls()
    {
        AddWall(new Vector2(WindowW / 2f, WindowH),      new Vector2(WindowW, 20));
        AddWall(new Vector2(WindowW / 2f, 0),             new Vector2(WindowW, 20));
        AddWall(new Vector2(0, WindowH / 2f),             new Vector2(20, WindowH));
        AddWall(new Vector2(WindowW, WindowH / 2f),       new Vector2(20, WindowH));
    }

    private void AddWall(Vector2 pos, Vector2 size)
    {
        var body = new StaticBody2D { Position = pos };
        var mat = new PhysicsMaterial { Bounce = 1f, Friction = 0f };
        body.PhysicsMaterialOverride = mat;
        var shape = new CollisionShape2D();
        var rect = new RectangleShape2D { Size = size };
        shape.Shape = rect;
        body.AddChild(shape);
        AddChild(body);
    }

    private void SpawnBall()
    {
        var body = new RigidBody2D
        {
            Position = new Vector2(
                (float)GD.RandRange(BallRadius + 15, WindowW - BallRadius - 15),
                (float)GD.RandRange(BallRadius + 15, WindowH - BallRadius - 15)
            ),
            LinearDamp = 0f,
            GravityScale = 0f,
            PhysicsMaterialOverride = new PhysicsMaterial { Bounce = 1f, Friction = 0f }
        };

        var shape = new CollisionShape2D();
        shape.Shape = new CircleShape2D { Radius = BallRadius };
        body.AddChild(shape);

        var sprite = new Sprite2D { Texture = _ballTexture };
        body.AddChild(sprite);

        body.LinearVelocity = new Vector2(
            (float)GD.RandRange(-200, 200),
            (float)GD.RandRange(-200, 200)
        );

        AddChild(body);
        _activeCount++;
    }

    public override void _Process(double delta)
    {
        if (_stopped) return;

        _spawnTimer += (float)delta;
        while (_spawnTimer >= _spawnInterval)
        {
            _spawnTimer -= _spawnInterval;
            SpawnBall();
        }

        int fps = Engine.GetFramesPerSecond();
        _fpsLabel.Text = $"FPS: {fps}";
        _countLabel.Text = $"Sprites: {_activeCount}";

        if (fps < MinFps && _activeCount > 50)
        {
            _stopped = true;
            _fpsLabel.Modulate = Colors.Red;
            _countLabel.Modulate = Colors.Red;
            _fpsLabel.Text += "  [STOP — FPS < 20]";
        }
    }
}
