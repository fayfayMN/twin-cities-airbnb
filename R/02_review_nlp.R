# =====================================================================
# TRACK B - STEP 5b: Review text mining in R (tidytext)
#
# This is where R clearly BEATS Python for beginners: tidytext makes
# tokenize -> remove stopwords -> join a sentiment lexicon a 4-line pipe.
# Reads the same outputs/reviews_clean.csv.
#
# Run:  Rscript R/02_review_nlp.R
# Needs: install.packages(c("tidyverse","tidytext"))
#        (first run of tidytext may prompt to download the 'bing'/'afinn' lexicon)
# =====================================================================
suppressPackageStartupMessages({
  library(tidyverse)
  library(tidytext)
})

out_dir <- "outputs"; fig_dir <- file.path(out_dir, "figures")

reviews <- read_csv(file.path(out_dir, "reviews_clean.csv"),
                    show_col_types = FALSE) %>%
  filter(!is.na(comments)) %>%
  slice_sample(n = 40000)          # sample for speed; remove for full 319K

# tokenize -> drop stop words
tokens <- reviews %>%
  select(listing_id, date, month, comments) %>%
  unnest_tokens(word, comments) %>%
  anti_join(stop_words, by = "word") %>%
  filter(str_detect(word, "^[a-z']+$"), nchar(word) > 2)

# ---- top words -----------------------------------------------------
p_top <- tokens %>%
  count(word, sort = TRUE) %>%
  slice_max(n, n = 20) %>%
  ggplot(aes(n, fct_reorder(word, n))) +
  geom_col(fill = "indigo") +
  labs(title = "Most common review words", x = "count", y = NULL) +
  theme_minimal()
ggsave(file.path(fig_dir, "R_08_top_words.png"), p_top, width = 8, height = 6, dpi = 130)

# ---- sentiment by month via the AFINN lexicon ----------------------
afinn <- get_sentiments("afinn")
month_sent <- tokens %>%
  inner_join(afinn, by = "word") %>%
  group_by(month) %>%
  summarise(sentiment = mean(value), .groups = "drop")

p_sent <- month_sent %>%
  ggplot(aes(factor(month), sentiment)) +
  geom_col(fill = "teal") +
  labs(title = "Mean review sentiment by month (AFINN)",
       x = "month", y = "avg word sentiment") +
  theme_minimal()
ggsave(file.path(fig_dir, "R_09_sentiment_by_month.png"), p_sent, width = 9, height = 4, dpi = 130)

# ---- words that drive positive vs negative (bing) ------------------
bing_contrib <- tokens %>%
  inner_join(get_sentiments("bing"), by = "word") %>%
  count(word, sentiment, sort = TRUE) %>%
  group_by(sentiment) %>%
  slice_max(n, n = 12) %>%
  ungroup()

p_bing <- bing_contrib %>%
  mutate(word = reorder_within(word, n, sentiment)) %>%
  ggplot(aes(n, word, fill = sentiment)) +
  geom_col(show.legend = FALSE) +
  facet_wrap(~sentiment, scales = "free_y") +
  scale_y_reordered() +
  labs(title = "Top positive vs negative words (bing lexicon)", y = NULL) +
  theme_minimal()
ggsave(file.path(fig_dir, "R_10_bing_words.png"), p_bing, width = 10, height = 5, dpi = 130)

cat("R text mining done. See R_08/09/10 in outputs/figures/\n")
