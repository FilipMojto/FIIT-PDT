# PDT Assignment 6 - Data Modelling in MongoDB

---

## Design

The database design was modeled as a simple schema resembling a physical data model commonly used in relational systems.
However, unlike traditional SQL modeling, the NoSQL model also supports embedded subdocuments and denormalized structures to improve read performance.

In this design, we applied several well-known MongoDB schema design patterns:

1) **Subset**
2) **Polymorphic Pattern**
3) **Outlier Pattern**

### Subset Pattern

The **Subset Pattern** is used in the Users collection for the attributes:

- latest_posts_followed
- my_latest_posts

These fields store only a small, frequently accessed subset of related posts (e.g., the last 3–5 posts).
This allows the application to immediately display a user's personal feed and the newest posts from followed users without scanning or joining the entire Tweets collection.

These embedded subsets may include extra attributes such as:

- post metadata
- basic author info
- the latest comments on the post

This pattern dramatically reduces the number of queries required to load a timeline.

### Polymorhpic Pattern

The **Polymorphic Pattern** is used in the Tweets collection. Each tweet may have a different structure based on the post type:

- type: "text" → stores text
- type: "image" → stores image_url, caption
- type: "video" → stores video_url, duration

etc.

MongoDB allows documents within the same collection to have heterogeneous fields, so there is no need to create multiple SQL tables such as text_posts, image_posts, video_posts.

### Outlier Pattern

The Outlier Pattern is used in the Tweets collection for storing high-level counts such as:

- total number of replies
- total number of likes
- number of users followed
- number of followers

These fields are stored as separate attributes, not as embedded documents.
This avoids loading huge arrays when the only required information is the count.

![Data Model](img/data_model.png)

## Design Rationale

### Subset Usage in the Users Collection

We applied the Subset Pattern in the Users collection for the attributes:

- *latest_posts_followed*
- *my_latest_posts*

These subsets store only a small, most frequently accessed portion of related posts.
When a user opens the application, one of the critical UX requirements is to load their feed as quickly as possible, without performing expensive queries across large collections.

By embedding the newest posts from followed users directly inside the user document:

- The feed loads immediately.
- No additional round-trip to the Tweets collection is required.
- Only the most relevant data is stored:
    - a short preview of the post,
    - a limited sample of comments,
    - author metadata such as *avatar* and *username*,
    - reaction counts like *likes_count* and *reactions_count*.

This denormalized representation drastically improves read performance for the most common action in a social media application: **loading the timeline**.

### Outlier Pattern for Counts

We used the Outlier Pattern in the Users collection for attributes such as:

- *posts_count*
- *following_count*
- *followers_count*

and similarly in the Posts collection for:

- *comments_count*
- *likes_count*

These values are stored as **top-level attributes**, not as embedded arrays.
The motivation is simple:

- Storing full embeddings (e.g., all follower IDs or all reaction objects) makes each user or post document grow excessively large.
- Reading large embedded arrays is slow and unnecessary when we only need the count.
- Keeping the counters as scalar values enables constant-time access and dramatically speeds up queries such as:

    - retrieving user profiles,
    - displaying post statistics,
    - ranking posts by popularity,
    - listing users by follower count.

This approach prevents loading potentially massive arrays and keeps frequently needed metrics lightweight and fast to access.
 
## JSON-like Examples

The json-like structure for the documents is already proposed in the diagram. However, we include some example instances:

### Example Documents

#### Users

```json
{
  "_id": ObjectId("675aaa100000000000000001"),
  "username": "filip",
  "avatar": "https://cdn.app/avatars/filip.png",
  "bio": "Software developer",
  "stats": {
    "posts_count": 34,
    "following_count": 88,
    "followers_count": 1200
  },
  "settings": {
    "private": false,
    "language": "sk"
  },

  "latest_posts_followed": [
    {
      "post_id": ObjectId("675aaa300000000000000011"),
      "username": "john",
      "avatar": "https://cdn.app/john.png",
      "text": "Hiking in the mountains!",
      "newest_comments": [
        {
          "username": "maria",
          "text": "Amazing view!"
        }
      ],
      "likes_count": 1400,
      "reactions_count": 1500
    }
  ],

  "my_latest_posts": [
    {
      "post_id": ObjectId("675aaa300000000000000021"),
      "type": "image",
      "image_url": "https://cdn.app/img/sky.jpg",
      "tags": ["sunset", "sky"],
      "text": null
    }
  ]
}
```

#### Posts

```json
{
  "_id": ObjectId("675aaa300000000000000011"),
  "author_id": ObjectId("675aaa100000000000000002"),
  "created_at": ISODate("2025-02-15T10:33:00Z"),
  "type": "image",
  "image_url": "https://cdn.app/img/sunset.png",
  "caption": "Beautiful sunset!",
  "text": null,
  "tags": ["sunset", "sky"],

  "comments_count": 412,
  "likes_count": 1400,

  "location": [48.1486, 17.1077]
}
```

#### Comments

```json
{
  "_id": ObjectId("675aac0000000000000000c1"),
  "post_id": ObjectId("675aaa300000000000000011"),
  "author_id": ObjectId("675aaa100000000000000001"),
  "text": "Amazing!",
  "created_at": ISODate("2025-02-15T10:35:10Z")
}
```

#### Reactions

```
{
  "_id": ObjectId("675aad0000000000000000f1"),
  "user_id": ObjectId("675aaa100000000000000001"),
  "target_id": ObjectId("675aac0000000000000000c1"),  // post OR comment
  "type": "like",
  "created_at": ISODate("2025-02-15T11:00:00Z")
}
```

#### Follows

```json
{
  "_id": ObjectId("675aab0000000000000000a1"),
  "follower_id": ObjectId("675aaa100000000000000001"),
  "followee_id": ObjectId("675aaa100000000000000002"),
  "created_at": ISODate("2025-02-14T18:00:00Z")
}
```

### CRUD Operation Examples

Below are some demonstrations of commonly used queries in our designed database.

#### Create a Post
```json
db.Posts.insertOne({
  author_id: ObjectId("675aaa100000000000000002"),
  created_at: new Date(),
  type: "text",
  text: "MongoDB is awesome!",
  tags: ["mongodb", "nosql"],
  comments_count: 0,
  likes_count: 0,
  location: [48.15, 17.10]
});
```

#### Insert a Reaction (Fast Write)

```json
db.Reactions.insertOne({
  user_id: ObjectId("675aaa100000000000000001"),
  target_id: ObjectId("675aaa300000000000000011"),
  type: "like",
  created_at: new Date()
});
```

Increment counter atomically:

```json
db.Posts.updateOne(
  { _id: ObjectId("675aaa300000000000000011") },
  { $inc: { likes_count: 1 } }
);
```

#### Get All Comments for a Post (Paginated)

```json
db.Comments.find({ post_id: POST_ID })
    .sort({ created_at: 1 })
    .skip(20)
    .limit(10);
```

#### User Feed – Load Posts From People I Follow

Step 1: Find the IDs the user follows

```json
const followees = db.Follows
    .find({ follower_id: USER_ID })
    .map(f => f.followee_id);
```

Step 2: Get posts from them

```json
db.Posts.find({ author_id: { $in: followees } })
        .sort({ created_at: -1 })
        .limit(50);
```

> This uses **Fan-Out on Read** but there is a subset on Users.latest_posts_followed for cached instant-load info

#### Seach Users

Create index:

```json
db.Users.createIndex({ username: "text" });
```

Automcomplete Query:

```json
db.Users.find({
  username: { $regex: "^fil", $options: "i" }
});
```

#### Search Hashtags
Search:

```json
db.Posts.find({ tags: "sunset" })
        .sort({ created_at: -1 })
        .limit(20);
```

Autocomplete:

```json
db.Posts.distinct("tags", { tags: { $regex: "^su", $options: "i" } });
```