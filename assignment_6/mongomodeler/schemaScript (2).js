db.createCollection("Reactions", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Reactions",
      required: ["_id", "user_id", "target_id", "type", "created_at"],
      properties: {
        "_id": { bsonType: "objectId" },
        "user_id": { bsonType: "objectId" },
        "target_id": { bsonType: "objectId" },
        "type": { bsonType: "enum" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("Comments", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Comments",
      required: ["_id", "post_id", "author_id", "created_at"],
      properties: {
        "_id": { bsonType: "objectId" },
        "post_id": { bsonType: "objectId" },
        "author_id": { bsonType: "objectId" },
        "text": { bsonType: "string" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});

db.createCollection("Posts", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Posts",
      required: ["_id", "created_at", "type"],
      properties: {
        "_id": { bsonType: "objectId" },
        "author_id": { bsonType: "objectId" },
        "created_at": { bsonType: "date" },
        "type": { bsonType: "enum" },
        "text": { bsonType: "string" },
        "image_url": { bsonType: "string" },
        "caption": { bsonType: "string" },
        "tags": { bsonType: "array" },
        "comments_count": { bsonType: "int" },
        "likes_count": { bsonType: "int" },
        "location": { bsonType: "array" },
      },
    },
  },
});

db.createCollection("Users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Users",
      required: ["_id", "latest_posts_followed"],
      properties: {
        "_id": { bsonType: "objectId" },
        "username": { bsonType: "string" },
        "avatar": { bsonType: "string" },
        "bio": { bsonType: "string" },
        "stats": { bsonType: "object", title: "stats", properties: { "posts_count": { bsonType: "int" }, "following_count": { bsonType: "int" }, "followers_count": { bsonType: "int" }, }, },
        "settings": { bsonType: "object", title: "settings", properties: { "private": { bsonType: "bool" }, "language": { bsonType: "enum" }, }, },
        "latest_posts_followed": { bsonType: "object", title: "latest_posts_followed", properties: { "avatar": { bsonType: "string" }, "username": { bsonType: "string" }, "newest_comments": { bsonType: "object", title: "newest_comments", properties: { "username": { bsonType: "string" }, "text": { bsonType: "string" }, }, }, "likes_count": { bsonType: "int" }, "reactions_count": { bsonType: "int" }, }, },
        "my_latest_posts": { bsonType: "object", title: "my_latest_posts", properties: { "image_url": { bsonType: "string" }, "tags": { bsonType: "string" }, "type": { bsonType: "string" }, "text": { bsonType: "string" }, }, },
      },
    },
  },
});

db.createCollection("Follows", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      title: "Follows",
      required: ["_id", "follower_id", "followee_id", "created_at"],
      properties: {
        "_id": { bsonType: "objectId" },
        "follower_id": { bsonType: "objectId" },
        "followee_id": { bsonType: "objectId" },
        "created_at": { bsonType: "date" },
      },
    },
  },
});