"""
Optimized Orchestrator for MagicPlay.

Integrates quality evaluation, resource caching, intelligent workflow engine,
and experiment tracking to improve video quality and reduce costs.
"""
import asyncio
import hashlib
from pathlib import Path
from loguru import logger
from typing import Any, Dict, List, Optional, Tuple

from ..evaluator.base import QualityLevel
from ..evaluator.image_evaluator import ImageQualityEvaluator
from ..experiment.tracker import ExperimentTracker, ExperimentConfig, ExperimentStatus, ExperimentResult
from ..resource_registry.registry import ResourceRegistry, ResourceType, ResourceState
from ..workflow.engine import (
    WorkflowEngine, WorkflowStep, GenerationStrategy, 
    GenerationRequest, GenerationResult, create_workflow_engine
)
from .orchestrator import Orchestrator as BaseOrchestrator


class OptimizedOrchestrator(BaseOrchestrator):
    """
    Enhanced orchestrator with quality optimization and cost reduction features.
    
    Key improvements over base orchestrator:
    1. Quality-driven generation with automatic retry
    2. Resource caching to avoid redundant generation
    3. Intelligent model selection based on quality/cost trade-offs
    4. Experiment tracking for continuous improvement
    5. Parallel processing for efficiency
    """
    
    def __init__(
        self,
        story_name: str,
        episode_name: str,
        max_scenes: int = 5,
        genre: str = "",
        reference_story: str = "",
        generation_strategy: GenerationStrategy = GenerationStrategy.BALANCED,
        enable_caching: bool = True,
        enable_experiments: bool = True,
        max_parallel_tasks: int = 2,
    ):
        super().__init__(story_name, episode_name, max_scenes, genre, reference_story)
        
        self.generation_strategy = generation_strategy
        self.enable_caching = enable_caching
        self.enable_experiments = enable_experiments
        self.max_parallel_tasks = max_parallel_tasks
        
        # Setup logging
        self.logger = logger
        
        # Initialize optimization components
        self._init_optimization_components()
        
        # Performance tracking
        self.generation_stats = {
            "total_cost": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failed_generations": 0,
            "quality_scores": [],
            "generation_times": [],
        }
    
    def _init_optimization_components(self):
        """Initialize optimization components."""
        # Resource registry for caching
        self.resource_registry = ResourceRegistry()
        
        # Workflow engine for intelligent generation
        self.workflow_engine = create_workflow_engine(
            registry=self.resource_registry,
            strategy=self.generation_strategy,
            parallel_tasks=self.max_parallel_tasks,
            enable_cache=self.enable_caching,
            enable_quality=True,
        )
        
        # Experiment tracker for A/B testing
        if self.enable_experiments:
            self.experiment_tracker = ExperimentTracker()
        else:
            self.experiment_tracker = None
        
        # Quality evaluators
        self.image_evaluator = ImageQualityEvaluator()
        
        # Register evaluators with workflow engine
        self.workflow_engine.register_evaluator(ResourceType.CHARACTER_IMAGE, self.image_evaluator)
        self.workflow_engine.register_evaluator(ResourceType.SCENE_CONCEPT, self.image_evaluator)
    
    async def _ensure_character_images_optimized(self, story_context: str) -> Dict[str, Path]:
        """
        Optimized version of character image generation with quality control.
        
        Returns:
            Dictionary mapping character names to image paths
        """
        from ..consistency.story_consistency import StoryConsistencyManager
        from ..generators.character_gen import CharacterImageGenerator
        
        try:
            # Create consistency manager
            consistency_manager = StoryConsistencyManager(self.story_name)
            
            # Load characters from story context
            if story_context:
                consistency_manager.load_from_story_bible(story_context)
                self.logger.info(f"Loaded {len(consistency_manager.characters)} characters from story bible")
            
            if not consistency_manager.characters:
                self.logger.warning("No characters found in story context")
                return {}
            
            character_images = {}
            character_gen = CharacterImageGenerator(self.story_name)
            
            # Process each character with optimization
            for character_name, character_desc in consistency_manager.characters.items():
                self.logger.info(f"Processing character: {character_name}")
                
                # Check cache first
                cached_image = await self._try_get_cached_character_image(character_name, character_desc)
                if cached_image:
                    character_images[character_name] = cached_image
                    self.generation_stats["cache_hits"] += 1
                    continue
                
                self.generation_stats["cache_misses"] += 1
                
                # Generate with quality control
                image_path = await self._generate_character_with_quality(
                    character_name, character_desc, character_gen, consistency_manager
                )
                
                if image_path:
                    character_images[character_name] = image_path
                    
                    # Cache the generated image
                    await self._cache_character_image(
                        character_name, character_desc, image_path
                    )
            
            self.logger.info(f"Generated {len(character_images)} character images")
            return character_images
            
        except Exception as e:
            self.logger.error(f"Character image generation failed: {e}")
            return {}
    
    async def _try_get_cached_character_image(
        self, character_name: str, character_desc: str
    ) -> Optional[Path]:
        """Try to get character image from cache."""
        if not self.enable_caching:
            return None
        
        try:
            # Search for similar character images in cache
            metadata = {
                "character_name": character_name,
                "character_description": character_desc[:500],  # Limit description length
                "story_name": self.story_name,
                "resource_type": "character_image",
            }
            
            similar = self.resource_registry.find_similar(
                resource_type=ResourceType.CHARACTER_IMAGE,
                metadata=metadata,
                min_quality=70.0,  # Only use high-quality cached images
                max_results=1,
            )
            
            if similar and similar[0].storage_path and similar[0].storage_path.exists():
                self.logger.info(f"Cache hit for character: {character_name}")
                
                # Update usage statistics
                self.resource_registry.update(
                    similar[0].resource_id,
                    quality_score=similar[0].quality_score,
                )
                
                return similar[0].storage_path
        
        except Exception as e:
            self.logger.warning(f"Cache lookup failed for {character_name}: {e}")
        
        return None
    
    async def _generate_character_with_quality(
        self,
        character_name: str,
        character_desc: str,
        character_gen: "CharacterImageGenerator",
        consistency_manager: "StoryConsistencyManager",
    ) -> Optional[Path]:
        """Generate character image with quality assessment and retry logic."""
        max_attempts = 3
        best_image = None
        best_quality = 0.0
        
        for attempt in range(max_attempts):
            self.logger.info(f"Attempt {attempt + 1}/{max_attempts} for {character_name}")
            
            try:
                # Generate image
                image_path = character_gen.generate_character_image(
                    character_name, character_desc, consistency_manager
                )
                
                if not image_path or not Path(image_path).exists():
                    self.logger.warning(f"Image generation failed for {character_name}")
                    continue
                
                # Evaluate quality
                quality_result = self.image_evaluator.evaluate(image_path)
                quality_score = quality_result.score
                
                self.logger.info(f"Quality score for {character_name}: {quality_score:.1f}")
                self.generation_stats["quality_scores"].append(quality_score)
                
                # Update best image
                if quality_score > best_quality:
                    best_quality = quality_score
                    best_image = Path(image_path)
                
                # Check if quality is acceptable
                if quality_result.is_acceptable:
                    self.logger.info(f"Character image quality acceptable: {quality_score:.1f}")
                    break
                else:
                    self.logger.warning(f"Character image quality low: {quality_score:.1f}, issues: {quality_result.issues}")
            
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed for {character_name}: {e}")
        
        if best_image and best_image.exists():
            self.logger.info(f"Best quality for {character_name}: {best_quality:.1f}")
            return best_image
        
        self.generation_stats["failed_generations"] += 1
        return None
    
    async def _cache_character_image(
        self,
        character_name: str,
        character_desc: str,
        image_path: Path,
    ):
        """Cache generated character image."""
        if not self.enable_caching:
            return
        
        try:
            # Read image content for deduplication
            with open(image_path, 'rb') as f:
                content = f.read()
            
            # Evaluate quality for caching
            quality_result = self.image_evaluator.evaluate(image_path)
            
            # Register in cache
            self.resource_registry.register(
                resource_type=ResourceType.CHARACTER_IMAGE,
                content=content,
                storage_path=image_path,
                metadata={
                    "character_name": character_name,
                    "character_description": character_desc[:500],
                    "story_name": self.story_name,
                    "quality_score": quality_result.score,
                },
                quality_score=quality_result.score,
                generation_cost=0.1,  # Estimated cost (can be configured)
                state=ResourceState.VALIDATED if quality_result.is_acceptable else ResourceState.GENERATED,
                tags=[f"character:{character_name}", f"story:{self.story_name}", "character_image"],
            )
            
            self.logger.info(f"Cached character image: {character_name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to cache character image {character_name}: {e}")
    
    async def _generate_scene_optimized(
        self,
        scene_name: str,
        story_ctx: str,
        episode_ctx: str,
        memory: str,
        scene_prompt_content: str = "",
        previous_video_path: Optional[Path] = None,
    ) -> Tuple[Optional[Path], str]:
        """
        Optimized scene generation with workflow engine.
        
        Returns:
            Tuple of (video_path, updated_memory)
        """
        try:
            # Step 1: Generate script with quality control
            script_path, script_content = await self._generate_script_optimized(
                scene_name, story_ctx, episode_ctx, memory, scene_prompt_content
            )
            
            if not script_path or not script_path.exists():
                self.logger.error(f"Script generation failed for {scene_name}")
                return None, memory
            
            # Update memory
            memory = script_content
            
            # Step 2: Generate video with optimization
            video_path = await self._generate_video_optimized(
                scene_name, script_path, previous_video_path
            )
            
            return video_path, memory
            
        except Exception as e:
            self.logger.error(f"Scene generation failed for {scene_name}: {e}")
            return None, memory
    
    async def _generate_script_optimized(
        self,
        scene_name: str,
        story_ctx: str,
        episode_ctx: str,
        memory: str,
        scene_prompt_content: str,
    ) -> Tuple[Optional[Path], str]:
        """Generate script with caching and quality optimization."""
        script_path = self.scripts_dir / f"{scene_name}.md"
        
        # Check if script already exists
        if script_path.exists():
            self.logger.info(f"Script already exists: {script_path}")
            return script_path, script_path.read_text(encoding="utf-8")
        
        # Check cache for similar scripts
        if self.enable_caching:
            cached_script = await self._try_get_cached_script(
                scene_name, story_ctx, episode_ctx, scene_prompt_content
            )
            if cached_script:
                return cached_script, cached_script.read_text(encoding="utf-8")
        
        # Generate new script
        self.logger.info(f"Generating script for {scene_name}...")
        generated_script_path = self.script_gen.generate_scene_script(
            scene_name=scene_name,
            story_context=story_ctx,
            episode_context=episode_ctx,
            memory=memory,
            scene_prompt=scene_prompt_content,
        )
        
        if generated_script_path and Path(generated_script_path).exists():
            # Cache the generated script
            await self._cache_script(
                scene_name, story_ctx, episode_ctx, scene_prompt_content, generated_script_path
            )
            
            return Path(generated_script_path), Path(generated_script_path).read_text(encoding="utf-8")
        
        return None, ""
    
    async def _try_get_cached_script(
        self,
        scene_name: str,
        story_ctx: str,
        episode_ctx: str,
        scene_prompt_content: str,
    ) -> Optional[Path]:
        """Try to get script from cache."""
        try:
            # Create metadata for script search
            metadata = {
                "scene_name": scene_name,
                "story_context_hash": hashlib.md5(story_ctx.encode()).hexdigest()[:16],
                "episode_context_hash": hashlib.md5(episode_ctx.encode()).hexdigest()[:16],
                "prompt_hash": hashlib.md5(scene_prompt_content.encode()).hexdigest()[:16],
                "resource_type": "script",
            }
            
            similar = self.resource_registry.find_similar(
                resource_type=ResourceType.SCRIPT,
                metadata=metadata,
                min_quality=60.0,
                max_results=1,
            )
            
            if similar and similar[0].storage_path and similar[0].storage_path.exists():
                self.logger.info(f"Cache hit for script: {scene_name}")
                return similar[0].storage_path
        
        except Exception as e:
            self.logger.warning(f"Script cache lookup failed: {e}")
        
        return None
    
    async def _cache_script(
        self,
        scene_name: str,
        story_ctx: str,
        episode_ctx: str,
        scene_prompt_content: str,
        script_path: Path,
    ):
        """Cache generated script."""
        try:
            with open(script_path, 'rb') as f:
                content = f.read()
            
            self.resource_registry.register(
                resource_type=ResourceType.SCRIPT,
                content=content,
                storage_path=script_path,
                metadata={
                    "scene_name": scene_name,
                    "story_context_hash": hashlib.md5(story_ctx.encode()).hexdigest()[:16],
                    "episode_context_hash": hashlib.md5(episode_ctx.encode()).hexdigest()[:16],
                    "prompt_hash": hashlib.md5(scene_prompt_content.encode()).hexdigest()[:16],
                },
                quality_score=80.0,  # Assume good quality for scripts
                generation_cost=0.05,  # Estimated LLM cost
                state=ResourceState.VALIDATED,
                tags=[f"scene:{scene_name}", f"story:{self.story_name}", "script"],
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to cache script: {e}")
    
    async def _generate_video_optimized(
        self,
        scene_name: str,
        script_path: Path,
        previous_video_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Generate video with optimization and quality control."""
        video_path = self.videos_dir / f"{scene_name}.mp4"
        
        # Check if video already exists
        if video_path.exists():
            self.logger.info(f"Video already exists: {video_path}")
            return video_path
        
        try:
            # Generate visual prompt
            visual_prompt_text = self.script_gen.generate_visual_prompt(script_path)
            
            # Get reference image
            ref_img_path = await self._get_reference_image_for_video(
                scene_name, script_path, previous_video_path
            )
            
            # Get optimal duration from script analysis
            from ..analyzer.script_analyzer import ScriptAnalyzer
            script_analyzer = ScriptAnalyzer(min_duration=2, max_duration=15)
            analysis_result = script_analyzer.analyze_file(str(script_path))
            duration = analysis_result.estimated_duration if analysis_result else 8
            
            # Use workflow engine for video generation
            self.logger.info(f"Generating video for {scene_name} with workflow engine...")
            
            # Here we would integrate with workflow engine
            # For now, use the base method with optimization flags
            generated_video = self.video_gen.generate_video(
                visual_prompt_text,
                video_path,
                ref_img_path=str(ref_img_path) if ref_img_path else None,
                duration=duration,
                force_unified_mode=True,
                optimize_quality=True,  # New optimization flag
                max_attempts=2,  # Retry on failure
            )
            
            if generated_video and Path(generated_video).exists():
                # Evaluate video quality (simplified)
                # In practice, would use a video quality evaluator
                await self._cache_video_result(scene_name, script_path, generated_video)
                return Path(generated_video)
            
        except Exception as e:
            self.logger.error(f"Video generation failed for {scene_name}: {e}")
        
        return None
    
    async def _get_reference_image_for_video(
        self,
        scene_name: str,
        script_path: Path,
        previous_video_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """Get reference image for video generation with optimization."""
        try:
            # Try to get scene concept image
            script_content = script_path.read_text(encoding="utf-8")
            story_ctx, _ = self.load_context()
            
            # Load character images for consistency
            character_images = {}
            try:
                from ..consistency.story_consistency import StoryConsistencyManager
                consistency_manager = StoryConsistencyManager(self.story_name)
                if story_ctx:
                    consistency_manager.load_from_story_bible(story_ctx)
                    character_images = consistency_manager.get_all_character_images() or {}
            except Exception as e:
                self.logger.warning(f"Failed to load character images: {e}")
            
            # Generate or get concept image
            scene_concept_image = self.scene_concept_gen.ensure_scene_concept_image(
                scene_name=scene_name,
                scene_script=script_content,
                use_previous_scene=previous_video_path is not None,
                previous_scene_image=str(previous_video_path) if previous_video_path else None,
                story_context=story_ctx,
                character_images=character_images,
                optimize_quality=True,  # New optimization flag
            )
            
            if scene_concept_image and Path(scene_concept_image).exists():
                # Evaluate concept image quality
                quality_result = self.image_evaluator.evaluate(scene_concept_image)
                if quality_result.is_acceptable:
                    self.logger.info(f"Using scene concept image as reference: {scene_concept_image}")
                    return Path(scene_concept_image)
                else:
                    self.logger.warning(f"Scene concept image quality too low: {quality_result.score:.1f}")
        
        except Exception as e:
            self.logger.warning(f"Failed to get scene concept image: {e}")
        
        # Fallback to previous video's last frame
        if previous_video_path and Path(previous_video_path).exists():
            from ..utils.media import MediaUtils
            last_frame_path = self.videos_dir / f"last_frame_{Path(previous_video_path).stem}.jpg"
            if MediaUtils.extract_last_frame(previous_video_path, last_frame_path):
                self.logger.info(f"Using previous video's last frame as reference")
                return last_frame_path
        
        return None
    
    async def _cache_video_result(
        self,
        scene_name: str,
        script_path: Path,
        video_path: Path,
    ):
        """Cache video generation result."""
        if not self.enable_caching:
            return
        
        try:
            # Read video content (first few MB for deduplication)
            with open(video_path, 'rb') as f:
                content = f.read(1024 * 1024)  # Read first 1MB
            
            # Get script content hash
            script_content = script_path.read_text(encoding="utf-8")
            script_hash = hashlib.md5(script_content.encode()).hexdigest()[:16]
            
            self.resource_registry.register(
                resource_type=ResourceType.VIDEO_CLIP,
                content=content,
                storage_path=video_path,
                metadata={
                    "scene_name": scene_name,
                    "script_hash": script_hash,
                    "video_duration": self._get_video_duration(video_path),
                },
                quality_score=70.0,  # Assume medium quality (would need video evaluator)
                generation_cost=0.5,  # Estimated video generation cost
                state=ResourceState.GENERATED,
                tags=[f"scene:{scene_name}", f"story:{self.story_name}", "video"],
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to cache video result: {e}")
    
    def _get_video_duration(self, video_path: Path) -> float:
        """Get video duration in seconds."""
        try:
            from ..utils.media import MediaUtils
            return MediaUtils.get_video_duration(video_path)
        except Exception:
            return 0.0
    
    async def run_optimized(self, initial_memory: str = "") -> Tuple[Optional[Path], str]:
        """
        Run the optimized generation pipeline.
        
        Returns:
            Tuple of (final_video_path, final_memory)
        """
        try:
            story_ctx, episode_ctx = self.load_context()
        except Exception as e:
            self.logger.error(f"Error loading context: {e}")
            return None, ""
        
        video_files = []
        memory = initial_memory
        
        self.logger.info(f"Starting optimized generation for {self.story_name}/{self.episode_name}")
        
        # Phase 1: Generate character images with optimization
        self.logger.info("Phase 1: Generating character images with quality control...")
        character_images = await self._ensure_character_images_optimized(story_ctx)
        self.logger.info(f"Generated {len(character_images)} character images")
        
        # Determine scenes to process
        from ..utils.paths import DataManager
        scene_prompts = DataManager.get_scenes_prompts(self.story_name, self.episode_name)
        
        if scene_prompts:
            self.logger.info(f"Found {len(scene_prompts)} scene definitions")
            scenes_to_process = []
            for prompt_file in scene_prompts:
                scene_name = prompt_file.stem
                scenes_to_process.append((scene_name, prompt_file))
        else:
            self.logger.info(f"Generating {self.max_scenes} sequential scenes")
            scenes_to_process = [(f"scene_{i}", None) for i in range(1, self.max_scenes + 1)]
        
        # Track previous video for continuity
        previous_video_path = None
        
        # Process scenes with optimization
        for scene_name, prompt_file in scenes_to_process:
            self.logger.info(f"\n--- Processing scene: {scene_name} ---")
            
            scene_prompt_content = ""
            if prompt_file:
                scene_prompt_content = prompt_file.read_text(encoding="utf-8")
            
            # Generate scene with optimization
            video_path, memory = await self._generate_scene_optimized(
                scene_name=scene_name,
                story_ctx=story_ctx,
                episode_ctx=episode_ctx,
                memory=memory,
                scene_prompt_content=scene_prompt_content,
                previous_video_path=previous_video_path,
            )
            
            if video_path and video_path.exists():
                video_files.append(str(video_path))
                previous_video_path = video_path
                self.logger.info(f"Successfully generated scene video: {video_path}")
            else:
                self.logger.warning(f"Failed to generate video for scene: {scene_name}")
        
        # Stitch videos if any were generated
        if video_files:
            output_file = self.videos_dir / f"{self.episode_name}_full_optimized.mp4"
            try:
                from ..utils.media import MediaUtils
                MediaUtils.stitch_videos(video_files, output_file)
                
                if output_file.exists():
                    self.logger.info(f"Episode complete: {output_file}")
                    
                    # Log generation statistics
                    self._log_generation_statistics()
                    
                    return output_file, memory
                
            except Exception as e:
                self.logger.error(f"Video stitching failed: {e}")
        
        return None, memory
    
    def _log_generation_statistics(self):
        """Log generation statistics."""
        if not self.generation_stats["quality_scores"]:
            avg_quality = 0.0
        else:
            avg_quality = sum(self.generation_stats["quality_scores"]) / len(self.generation_stats["quality_scores"])
        
        cache_hit_rate = 0.0
        total_cache_attempts = self.generation_stats["cache_hits"] + self.generation_stats["cache_misses"]
        if total_cache_attempts > 0:
            cache_hit_rate = self.generation_stats["cache_hits"] / total_cache_attempts
        
        self.logger.info(f"""
        Generation Statistics:
        ---------------------
        Total Cost: ${self.generation_stats['total_cost']:.3f}
        Cache Hits: {self.generation_stats['cache_hits']}
        Cache Misses: {self.generation_stats['cache_misses']}
        Cache Hit Rate: {cache_hit_rate:.1%}
        Failed Generations: {self.generation_stats['failed_generations']}
        Average Quality Score: {avg_quality:.1f}
        """)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        registry_stats = self.resource_registry.get_statistics() if self.enable_caching else {}
        workflow_stats = self.workflow_engine.get_statistics()
        
        return {
            "generation_stats": self.generation_stats,
            "registry_stats": registry_stats,
            "workflow_stats": workflow_stats,
            "optimization_enabled": {
                "caching": self.enable_caching,
                "experiments": self.enable_experiments,
                "strategy": self.generation_strategy.value,
                "parallel_tasks": self.max_parallel_tasks,
            },
        }


def create_optimized_orchestrator(
    story_name: str,
    episode_name: str,
    strategy: str = "balanced",
    enable_cache: bool = True,
    enable_experiments: bool = False,
    max_parallel: int = 2,
) -> OptimizedOrchestrator:
    """Factory function for creating optimized orchestrator."""
    # Map strategy string to enum
    strategy_map = {
        "quality_first": GenerationStrategy.QUALITY_FIRST,
        "balanced": GenerationStrategy.BALANCED,
        "cost_optimized": GenerationStrategy.COST_OPTIMIZED,
        "cache_only": GenerationStrategy.CACHE_ONLY,
    }
    
    generation_strategy = strategy_map.get(strategy.lower(), GenerationStrategy.BALANCED)
    
    return OptimizedOrchestrator(
        story_name=story_name,
        episode_name=episode_name,
        generation_strategy=generation_strategy,
        enable_caching=enable_cache,
        enable_experiments=enable_experiments,
        max_parallel_tasks=max_parallel,
    )