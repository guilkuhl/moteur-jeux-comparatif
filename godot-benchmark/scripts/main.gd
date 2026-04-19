extends Node2D

const WINDOW_W := 960
const WINDOW_H := 1080
const SPAWN_PER_SECOND := 10
const MIN_FPS := 20.0
const BALL_RADIUS := 2.0

var ball_texture: ImageTexture
var spawn_timer := 0.0
var spawn_interval := 1.0 / SPAWN_PER_SECOND
var active_count := 0
var stopped := false

@onready var fps_label: Label = $UI/VBox/FPSLabel
@onready var count_label: Label = $UI/VBox/CountLabel

func _ready() -> void:
	_generate_ball_texture()
	_create_walls()

func _generate_ball_texture() -> void:
	var img := Image.create(16, 16, false, Image.FORMAT_RGBA8)
	var center := Vector2(8.0, 8.0)
	for x in range(16):
		for y in range(16):
			var dist := Vector2(x + 0.5, y + 0.5).distance_to(center)
			img.set_pixel(x, y, Color(0.3, 0.7, 1.0, 1.0) if dist <= 7.5 else Color.TRANSPARENT)
	ball_texture = ImageTexture.create_from_image(img)

func _create_walls() -> void:
	_add_wall(Vector2(WINDOW_W / 2.0, WINDOW_H),     Vector2(WINDOW_W, 20))
	_add_wall(Vector2(WINDOW_W / 2.0, 0),             Vector2(WINDOW_W, 20))
	_add_wall(Vector2(0, WINDOW_H / 2.0),             Vector2(20, WINDOW_H))
	_add_wall(Vector2(WINDOW_W, WINDOW_H / 2.0),      Vector2(20, WINDOW_H))

func _add_wall(pos: Vector2, size: Vector2) -> void:
	var body := StaticBody2D.new()
	body.position = pos
	var mat := PhysicsMaterial.new()
	mat.bounce = 1.0
	mat.friction = 0.0
	body.physics_material_override = mat
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = size
	shape.shape = rect
	body.add_child(shape)
	add_child(body)

func _spawn_ball() -> void:
	var body := RigidBody2D.new()
	body.position = Vector2(
		randf_range(BALL_RADIUS + 15, WINDOW_W - BALL_RADIUS - 15),
		randf_range(BALL_RADIUS + 15, WINDOW_H - BALL_RADIUS - 15)
	)
	body.linear_damp = 0.0
	body.gravity_scale = 0.0
	var mat := PhysicsMaterial.new()
	mat.bounce = 1.0
	mat.friction = 0.0
	body.physics_material_override = mat
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = BALL_RADIUS
	shape.shape = circle
	body.add_child(shape)
	var sprite := Sprite2D.new()
	sprite.texture = ball_texture
	body.add_child(sprite)
	body.linear_velocity = Vector2(randf_range(-200, 200), randf_range(-200, 200))
	add_child(body)
	active_count += 1

func _process(delta: float) -> void:
	if stopped:
		return
	spawn_timer += delta
	while spawn_timer >= spawn_interval:
		spawn_timer -= spawn_interval
		_spawn_ball()
	var fps := Engine.get_frames_per_second()
	fps_label.text = "FPS: %d" % fps
	count_label.text = "Sprites: %d" % active_count
	if fps < MIN_FPS and active_count > 50:
		stopped = true
		fps_label.modulate = Color.RED
		count_label.modulate = Color.RED
		fps_label.text += "  [STOP — FPS < 20]"
